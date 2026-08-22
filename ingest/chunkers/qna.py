"""Chunker for the scraped Sistani Q&A text file.

This source is already structured as `===== Topic =====` blocks containing numbered
`Qn:` / `An:` pairs, so a Q&A pair is treated as the atomic unit: the question is kept
together with its answer because neither retrieves usefully alone.
"""

from __future__ import annotations

import re

from ingest.base import Chunk, TOKEN_CAPS, emit
from ingest.extract import clean_text

PATH = "data/sistani_qna.txt"
DOC_ID = "sistani_qna"

_TOPIC = re.compile(r"^=====\s*(.+?)\s*=====\s*$")
_Q = re.compile(r"^Q(\d+):\s*:?\s*(.*)$")
_A = re.compile(r"^A(\d+):\s*:?\s*(.*)$")


def chunk_sistani_qna(path: str = PATH) -> list[Chunk]:
    cap = TOKEN_CAPS[DOC_ID]
    with open(path, encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    chunks: list[Chunk] = []
    topic: str | None = None
    q_num: str | None = None
    q_text: list[str] = []
    a_text: list[str] = []
    mode: str | None = None

    def flush() -> None:
        nonlocal q_num, q_text, a_text, mode
        if q_num and (q_text or a_text):
            q = clean_text(" ".join(q_text)).strip()
            a = clean_text(" ".join(a_text)).strip()
            body = f"Question: {q}\nAnswer: {a}" if a else f"Question: {q}"
            emit(
                chunks, DOC_ID, body, cap,
                chapter=topic,
                section=None,
                locator=f"Q{q_num}",
                extra={"question": q},
            )
        q_num, q_text, a_text, mode = None, [], [], None

    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        m_topic = _TOPIC.match(stripped)
        if m_topic:
            flush()
            topic = clean_text(m_topic.group(1))
            continue
        m_q = _Q.match(stripped)
        if m_q:
            flush()
            q_num = m_q.group(1)
            q_text = [m_q.group(2)]
            mode = "q"
            continue
        m_a = _A.match(stripped)
        if m_a:
            a_text = [m_a.group(2)]
            mode = "a"
            continue
        if mode == "q":
            q_text.append(stripped)
        elif mode == "a":
            a_text.append(stripped)

    flush()
    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks
