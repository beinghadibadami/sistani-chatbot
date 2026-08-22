"""Query the built index and compare retrieval modes.

    python tools/search.py "Is abortion permissible?"
    python tools/search.py "inheritance shares" -k 8 --mode dense
    python tools/search.py "Friday prayer verses" --compare
    python tools/search.py "Friday prayer verses" --rerank
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from rag.retrieve import Retriever


def show(hits, full: bool) -> None:
    for i, h in enumerate(hits, 1):
        extra = f"  rerank={h.rerank_score:.3f}" if h.rerank_score is not None else ""
        print(f"  [{i}] {h.score:.4f} [{h.source:<5}]{extra}  {h.citation}")
        body = h.text if full else (h.text[:200].replace("\n", " ") + ("..." if len(h.text) > 200 else ""))
        print(f"      {body}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--backend", default=None, choices=("local", "api"))
    ap.add_argument("--mode", default="hybrid", choices=("hybrid", "dense", "bm25"))
    ap.add_argument("--compare", action="store_true", help="run all three modes side by side")
    ap.add_argument("--rerank", action="store_true", help="enable cross-encoder reranking")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    question = " ".join(args.question)
    r = Retriever(backend=args.backend, rerank=args.rerank)
    print(f"backend={r.backend}  vectors={r.count}  rerank={r.rerank_enabled}")
    print(f"\nQ: {question}")

    modes = ("dense", "bm25", "hybrid") if args.compare else (args.mode,)
    for mode in modes:
        t0 = time.perf_counter()
        hits = r.search(question, k=args.k, mode=mode)
        dt = (time.perf_counter() - t0) * 1000
        print(f"\n--- {mode.upper()}  ({dt:.0f} ms) ---")
        show(hits, args.full)


if __name__ == "__main__":
    main()
