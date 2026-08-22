"""Persistence for the index: FAISS vectors plus queryable SQLite metadata.

Design notes:
  - `IndexFlatIP` on unit vectors is exact cosine similarity. The previous pipeline used
    `IndexFlatL2`, which ranks by Euclidean distance and is not what BGE is trained for.
  - Metadata lives in SQLite rather than a pickle so citations can be filtered and
    inspected with real queries, and so rows can be added without rewriting a blob.
  - Row IDs are the FAISS vector positions, which is what makes lookup after search a
    direct primary-key hit.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import faiss
import numpy as np

INDEX_PATH = "artifacts/index.faiss"
DB_PATH = "artifacts/chunks.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY,   -- matches the FAISS vector position
    doc_id      TEXT NOT NULL,
    text        TEXT NOT NULL,         -- clean body: what the LLM and UI receive
    embed_text  TEXT NOT NULL,         -- header + body: what was vectorised and BM25-indexed
    chapter     TEXT,
    section     TEXT,
    locator     TEXT,
    citation    TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    part        INTEGER,
    part_of     INTEGER,
    n_tokens    INTEGER NOT NULL,
    extra       TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc     ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_locator ON chunks(doc_id, locator);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# BM25 lexical index, used as the sparse half of hybrid retrieval.
#
# FTS5 ships with Python's sqlite3, so this adds no dependency and no memory cost: the
# index lives on disk rather than as tokenised documents in RAM, which matters on a 512 MB
# host. `content='chunks'` makes it an external-content table so chunk text is not stored
# twice. Porter stemming lets 'praying' match 'prayer'.
# `embed_text` is indexed rather than `text`, so chapter/section/locator words are
# lexically searchable: BM25 can then reach every chunk of a chapter by its name (e.g.
# "Irth", "al-Jumu'ah"), which the body text alone often never mentions.
FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    embed_text,
    content='chunks',
    content_rowid='id',
    tokenize='porter unicode61'
);
"""


def write_store(
    chunks: list,
    vectors: np.ndarray,
    *,
    index_path: str = INDEX_PATH,
    db_path: str = DB_PATH,
    model_name: str,
) -> None:
    """Write the FAISS index and metadata DB, replacing any previous build."""
    if len(chunks) != vectors.shape[0]:
        raise ValueError(
            f"chunk/vector count mismatch: {len(chunks)} chunks vs {vectors.shape[0]} vectors"
        )

    Path(index_path).parent.mkdir(parents=True, exist_ok=True)

    vectors = np.ascontiguousarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise ValueError(
            "vectors are not unit length; inner-product search would not equal cosine"
        )

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, index_path)

    Path(db_path).unlink(missing_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            """INSERT INTO chunks
               (id, doc_id, text, embed_text, chapter, section, locator, citation,
                chunk_index, part, part_of, n_tokens, extra)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    i,
                    c.doc_id,
                    c.text,
                    c.embed_text(),
                    c.chapter,
                    c.section,
                    c.locator,
                    c.citation(),
                    c.chunk_index,
                    c.part,
                    c.part_of,
                    c.n_tokens,
                    json.dumps(c.extra) if c.extra else None,
                )
                for i, c in enumerate(chunks)
            ],
        )
        conn.executescript(FTS_SCHEMA)
        # Populate the external-content FTS index from the chunks table.
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        conn.executemany(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)",
            [
                ("model_name", model_name),
                ("dim", str(vectors.shape[1])),
                ("count", str(len(chunks))),
                ("metric", "inner_product/cosine"),
                ("fts", "fts5/bm25 porter unicode61 over embed_text"),
                ("contextual_headers", "1"),
            ],
        )
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()


def load_index(index_path: str = INDEX_PATH):
    return faiss.read_index(index_path)


def connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_chunks(conn: sqlite3.Connection, ids: list[int]) -> list[dict]:
    """Fetch metadata rows for FAISS hit positions, preserving the ranking order."""
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM chunks WHERE id IN ({placeholders})", ids
    ).fetchall()
    by_id = {r["id"]: dict(r) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


_FTS_TOKEN = re.compile(r"[A-Za-z0-9']+")


def fts_query_string(question: str) -> str:
    """Turn free text into a safe FTS5 MATCH expression.

    Raw questions contain characters that are FTS5 operators (quotes, hyphens, parentheses)
    and would raise a syntax error, so only word tokens are kept. Terms are OR-ed for
    recall and then ranked by BM25; requiring every term would return nothing for most
    natural questions.
    """
    tokens = [t for t in _FTS_TOKEN.findall(question) if len(t) > 1]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens)


def bm25_search(
    conn: sqlite3.Connection,
    question: str,
    k: int = 30,
    match: str | None = None,
    doc_ids: set[str] | None = None,
) -> list[tuple[int, float]]:
    """Lexical search. Returns [(chunk_id, score)] best-first.

    `match` allows the caller to pass a prebuilt (e.g. synonym-expanded) MATCH expression;
    otherwise the question is tokenised as-is.

    FTS5's bm25() returns more-negative values for better matches, so it is negated to
    make a larger score mean a better match, matching the dense side's convention.
    """
    match = match if match is not None else fts_query_string(question)
    if not match:
        return []

    if doc_ids:
        docs = list(doc_ids)
        placeholders = ",".join("?" * len(docs))
        rows = conn.execute(
            f"""SELECT f.rowid AS id, bm25(chunks_fts) AS score
                FROM chunks_fts f
                JOIN chunks c ON c.id = f.rowid
                WHERE chunks_fts MATCH ? AND c.doc_id IN ({placeholders})
                ORDER BY score
                LIMIT ?""",
            (match, *docs, k),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT rowid AS id, bm25(chunks_fts) AS score
               FROM chunks_fts
               WHERE chunks_fts MATCH ?
               ORDER BY score
               LIMIT ?""",
            (match, k),
        ).fetchall()
    return [(int(r["id"]), -float(r["score"])) for r in rows]
