"""Quantify the cost of prepending citation headers before committing to a rebuild.

BGE truncates at 512 tokens. Chunk caps are already 500 for the legal documents, so a
header could push chunks past the limit and silently drop their tails. This reports how
many chunks would overflow and by how much.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.base import TOKEN_CAPS, count_tokens
from ingest.chunkers import CHUNKERS

BGE_LIMIT = 512


def main() -> None:
    total = 0
    overflow = 0
    header_tokens: list[int] = []
    worst = 0

    print(f"{'doc_id':<20} {'chunks':>7} {'cap':>5} {'hdr_avg':>8} {'hdr_max':>8} {'over512':>8}")
    print("-" * 62)

    for doc_id in sorted(CHUNKERS):
        chunks = CHUNKERS[doc_id]()
        # Measure embed_header()/embed_text(), which is what is actually vectorised;
        # the full citation() is only a display string and is not budgeted.
        hdrs = [count_tokens(c.embed_header()) for c in chunks]
        combined = [count_tokens(c.embed_text()) for c in chunks]
        over = sum(1 for t in combined if t > BGE_LIMIT)

        total += len(chunks)
        overflow += over
        header_tokens.extend(hdrs)
        worst = max(worst, max(combined))

        print(f"{doc_id:<20} {len(chunks):>7} {TOKEN_CAPS[doc_id]:>5} "
              f"{sum(hdrs)/len(hdrs):>8.1f} {max(hdrs):>8} {over:>8}")

    print("-" * 62)
    print(f"{'TOTAL':<20} {total:>7} {'':>5} "
          f"{sum(header_tokens)/len(header_tokens):>8.1f} {max(header_tokens):>8} {overflow:>8}")
    print(f"\nworst combined length: {worst} tokens (BGE limit {BGE_LIMIT})")
    print(f"overflowing chunks   : {overflow} / {total} ({100*overflow/total:.2f}%)")
    print(f"extra tokens to embed: {sum(header_tokens):,}")


if __name__ == "__main__":
    main()
