"""Run every chunker and report totals. Entry point for the next step (embedding + index).

    python -m ingest.run_all
"""

from __future__ import annotations

from ingest.base import TOKEN_CAPS
from ingest.chunkers import CHUNKERS


def build_all() -> dict[str, list]:
    """Chunk every document. Returns {doc_id: [Chunk, ...]}."""
    return {doc_id: fn() for doc_id, fn in CHUNKERS.items()}


def main() -> None:
    all_chunks = build_all()
    total = 0
    total_tokens = 0
    print(f"{'doc_id':<20} {'chunks':>7} {'cap':>5} {'tokens':>9} {'mean':>7}")
    print("-" * 52)
    for doc_id, chunks in all_chunks.items():
        toks = sum(c.n_tokens for c in chunks)
        total += len(chunks)
        total_tokens += toks
        mean = round(toks / len(chunks), 1) if chunks else 0
        print(f"{doc_id:<20} {len(chunks):>7} {TOKEN_CAPS[doc_id]:>5} {toks:>9} {mean:>7}")
    print("-" * 52)
    print(f"{'TOTAL':<20} {total:>7} {'':>5} {total_tokens:>9}")


if __name__ == "__main__":
    main()
