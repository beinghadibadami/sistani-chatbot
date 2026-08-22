"""Measure cross-encoder reranking cost, to decide whether it fits a 0.1-CPU host."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from rag.retrieve import Retriever

QUESTION = "Which verses describe the Friday congregational prayer?"

r = Retriever(backend="local", rerank=True)

# Pull a shortlist without reranking, so the timing below isolates the reranker.
hits = r.search(QUESTION, k=30, mode="hybrid", candidates=30)
docs = [h.text for h in hits]
avg_chars = sum(len(d) for d in docs) / len(docs)
print(f"shortlist: {len(docs)} docs, avg {avg_chars:.0f} chars")

t0 = time.perf_counter()
r._reranker.score(QUESTION, docs[:1])       # warm up / load model
print(f"model load + 1 pair: {time.perf_counter() - t0:.2f}s")

for n in (5, 10, 30):
    subset = docs[:n]
    t0 = time.perf_counter()
    r._reranker.score(QUESTION, subset)
    dt = time.perf_counter() - t0
    print(f"  rerank {n:>2} docs: {dt:6.2f}s  ({dt/n*1000:6.0f} ms/doc)")
