"""Hybrid retrieval: dense (FAISS/BGE) + lexical (SQLite FTS5/BM25), fused by RRF,
with optional cross-encoder reranking.

Why hybrid: dense search matches meaning but can miss exact wording, and it ranked fiqh
manuals above Quran 62:9-11 for "Which verses describe the Friday congregational prayer?"
because the manuals repeat the phrase while the verse says "Congregation Day". BM25 catches
that literal overlap, so the two are complementary.

Fusion uses Reciprocal Rank Fusion rather than score averaging, because cosine similarity
and BM25 are on incomparable scales; RRF only consumes the *rank* from each list, so no
score normalisation is needed.

Optional stage 2 is a cross-encoder, which scores (query, document) jointly instead of
comparing independent embeddings. It is more accurate but cannot be precomputed, so it runs
only over the fused shortlist. It is OFF by default: on a 0.1-CPU host it would dominate the
latency budget.

Env vars:
  EMBED_BACKEND  api (default) | local
  RERANK         0 (default) | 1
  RERANK_MODEL   Xenova/ms-marco-MiniLM-L-6-v2
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from ingest.embed import get_embedder
from ingest.store import (
    DB_PATH,
    INDEX_PATH,
    bm25_search,
    connect,
    fetch_chunks,
    load_index,
)
from rag.expand import detect_doc_intent, expanded_fts_query

RRF_K = 60          # standard RRF damping constant
CANDIDATES = 30     # shortlist size fed to fusion/reranking
DEPTH = 150         # per-retriever depth before fusion; deeper than CANDIDATES so that
                    # intent boosting has lower-ranked but relevant material to promote
INTENT_RESERVE = 0.4  # fraction of k reserved for explicitly requested doc types


@dataclass
class Hit:
    """One retrieved chunk with its citation metadata and provenance."""

    score: float
    text: str
    citation: str
    doc_id: str
    chapter: str | None = None
    section: str | None = None
    locator: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    dense_rank: int | None = None
    bm25_rank: int | None = None
    intent_rank: int | None = None
    rerank_score: float | None = None

    @property
    def source(self) -> str:
        """Which retriever(s) surfaced this chunk; useful for debugging relevance."""
        if self.intent_rank is not None and self.dense_rank is None and self.bm25_rank is None:
            return "intent"
        if self.dense_rank is not None and self.bm25_rank is not None:
            return "both"
        if self.dense_rank is not None:
            return "dense"
        return "bm25"


def rrf_fuse(
    ranked_lists: dict[str, list[int]], k: int = RRF_K
) -> list[tuple[int, float, dict[str, int]]]:
    """Reciprocal Rank Fusion over several ranked ID lists.

    Each list contributes 1/(k + rank) per document. Returns
    [(chunk_id, fused_score, {list_name: rank})] best-first.
    """
    scores: dict[int, float] = {}
    ranks: dict[int, dict[str, int]] = {}
    for name, ids in ranked_lists.items():
        for rank, cid in enumerate(ids, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            ranks.setdefault(cid, {})[name] = rank
    order = sorted(scores, key=lambda c: -scores[c])
    return [(cid, scores[cid], ranks[cid]) for cid in order]


class Reranker:
    """Cross-encoder reranker. Model loads lazily so it costs nothing when disabled."""

    def __init__(self, model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._model = TextCrossEncoder(model_name=self.model_name)
        return self._model

    def score(self, query: str, documents: list[str]) -> list[float]:
        return [float(s) for s in self.model.rerank(query, documents)]


class Retriever:
    def __init__(
        self,
        index_path: str = INDEX_PATH,
        db_path: str = DB_PATH,
        backend: str | None = None,
        rerank: bool | None = None,
        rerank_model: str | None = None,
        expand: bool | None = None,
    ):
        self.index = load_index(index_path)
        self.conn = connect(db_path)
        self.backend = backend or os.getenv("EMBED_BACKEND", "api")
        self.embedder = get_embedder(self.backend)
        self.expand = os.getenv("EXPAND", "1") == "1" if expand is None else expand

        if rerank is None:
            rerank = os.getenv("RERANK", "0") == "1"
        self.rerank_enabled = rerank
        self._reranker = (
            Reranker(rerank_model or os.getenv("RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2"))
            if rerank
            else None
        )

        row = self.conn.execute("SELECT value FROM meta WHERE key='count'").fetchone()
        self.count = int(row["value"]) if row else self.index.ntotal
        if self.index.ntotal != self.count:
            raise RuntimeError(
                f"index/metadata mismatch: {self.index.ntotal} vectors vs {self.count} rows"
            )

    # --- individual retrievers -------------------------------------------------

    def dense_search(
        self, question: str, k: int, doc_ids: set[str] | None = None
    ) -> list[tuple[int, float]]:
        vec = self.embedder.embed_query(question).reshape(1, -1).astype(np.float32)
        # IndexFlatIP cannot filter natively, so scoped search retrieves deeper and drops
        # non-matching docs afterwards. Cheap at this corpus size (a few thousand vectors).
        fetch = min(self.index.ntotal, k * 6 if doc_ids else k)
        scores, ids = self.index.search(vec, fetch)
        pairs = [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]
        if doc_ids:
            allowed = self._docs_of([cid for cid, _ in pairs])
            pairs = [(cid, s) for cid, s in pairs if allowed.get(cid) in doc_ids]
        return pairs[:k]

    def lexical_search(
        self, question: str, k: int, doc_ids: set[str] | None = None
    ) -> list[tuple[int, float]]:
        match = expanded_fts_query(question) if self.expand else None
        return bm25_search(self.conn, question, k, match=match, doc_ids=doc_ids)

    def _docs_of(self, ids: list[int]) -> dict[int, str]:
        if not ids:
            return {}
        placeholders = ",".join("?" * len(ids))
        return {
            int(r["id"]): r["doc_id"]
            for r in self.conn.execute(
                f"SELECT id, doc_id FROM chunks WHERE id IN ({placeholders})", ids
            )
        }

    def _intent_candidates(
        self, question: str, intent: set[str], n: int
    ) -> list[tuple[int, float, dict[str, int]]]:
        """Retrieve the best candidates restricted to explicitly requested doc types.

        A plain score multiplier cannot achieve this: RRF gives a rank-118 document ~0.0056
        against ~0.032 at the top, so promoting it would need an arbitrary ~6x factor that
        would distort every other query. Running a scoped retrieval and reserving slots is
        deterministic and only affects questions that actually name a source type.
        """
        match = expanded_fts_query(question) if self.expand else None
        scoped = bm25_search(self.conn, question, n, match=match, doc_ids=intent)
        return [(cid, score, {"intent": rank}) for rank, (cid, score) in enumerate(scoped, 1)]

    # --- public API -----------------------------------------------------------

    def search(
        self,
        question: str,
        k: int = 5,
        *,
        mode: Literal["hybrid", "dense", "bm25"] = "hybrid",
        candidates: int = CANDIDATES,
        depth: int = DEPTH,
        doc_ids: set[str] | None = None,
    ) -> list[Hit]:
        """Retrieve the k most relevant chunks, best first.

        `doc_ids` scopes the search to specific sources. Explicit user scoping is preferred
        over inferring intent from wording, so when it is supplied the intent heuristic is
        skipped entirely.
        """
        dense = (
            self.dense_search(question, depth, doc_ids)
            if mode in ("hybrid", "dense")
            else []
        )
        lexical = (
            self.lexical_search(question, depth, doc_ids)
            if mode in ("hybrid", "bm25")
            else []
        )

        if mode == "dense":
            shortlist = [(cid, s, {"dense": r}) for r, (cid, s) in enumerate(dense, 1)]
        elif mode == "bm25":
            shortlist = [(cid, s, {"bm25": r}) for r, (cid, s) in enumerate(lexical, 1)]
        else:
            shortlist = rrf_fuse(
                {
                    "dense": [cid for cid, _ in dense],
                    "bm25": [cid for cid, _ in lexical],
                }
            )

        if not shortlist:
            return []

        # Honour explicit source intent ("which verses...") by reserving slots for a
        # retrieval scoped to the requested doc types, so they cannot be crowded out by
        # the sheer volume of fiqh material.
        intent = (
            detect_doc_intent(question)
            if (self.expand and mode != "dense" and not doc_ids)
            else set()
        )
        reserved: list[tuple[int, float, dict[str, int]]] = []
        if intent:
            n_reserved = max(1, int(round(k * INTENT_RESERVE)))
            already = {cid for cid, _, _ in shortlist[:k]}
            for cand in self._intent_candidates(question, intent, n_reserved * 3):
                if cand[0] not in already:
                    reserved.append(cand)
                if len(reserved) >= n_reserved:
                    break

        shortlist = shortlist[:candidates]
        all_ids = [c for c, _, _ in shortlist] + [c for c, _, _ in reserved]
        rows = {r["id"]: r for r in fetch_chunks(self.conn, all_ids)}

        def build(entry: tuple[int, float, dict[str, int]]) -> Hit | None:
            cid, score, ranks = entry
            row = rows.get(cid)
            if row is None:
                return None
            return Hit(
                score=score,
                text=row["text"],
                citation=row["citation"],
                doc_id=row["doc_id"],
                chapter=row["chapter"],
                section=row["section"],
                locator=row["locator"],
                extra=json.loads(row["extra"]) if row["extra"] else {},
                dense_rank=ranks.get("dense"),
                bm25_rank=ranks.get("bm25"),
                intent_rank=ranks.get("intent"),
            )

        hits = [h for h in (build(e) for e in shortlist) if h is not None]

        if self._reranker is not None and hits:
            # Reranking makes the reserved slots unnecessary: the cross-encoder scores the
            # scoped candidates on equal terms with the rest, so they are merged in first.
            merged = hits + [h for h in (build(e) for e in reserved) if h is not None]
            scores = self._reranker.score(question, [h.text for h in merged])
            for hit, s in zip(merged, scores):
                hit.rerank_score = s
            merged.sort(key=lambda h: -(h.rerank_score or 0.0))
            return merged[:k]

        if not reserved:
            return hits[:k]

        # Interleave: keep the strongest fused results, then append the reserved
        # intent-scoped results, so both are represented within k.
        n_reserved = min(len(reserved), max(1, int(round(k * INTENT_RESERVE))))
        primary = hits[: max(0, k - n_reserved)]
        extra_hits = [h for h in (build(e) for e in reserved[:n_reserved]) if h is not None]
        return (primary + extra_hits)[:k]


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    """Process-wide singleton, so the index is read from disk only once."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
