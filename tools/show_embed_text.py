"""Print sample embed_text values so the header format can be reviewed before a rebuild."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.base import count_tokens
from ingest.chunkers import CHUNKERS

for doc_id in sorted(CHUNKERS):
    chunks = CHUNKERS[doc_id]()
    # A short chunk shows the header clearly; the longest verifies the budget holds.
    by_len = sorted(chunks, key=lambda c: c.n_tokens)
    samples = [by_len[len(by_len) // 2], by_len[-1]]
    print("=" * 92)
    print(f"{doc_id}  ({len(chunks)} chunks)")
    print("=" * 92)
    for c in samples:
        et = c.embed_text()
        print(f"  header tokens={count_tokens(c.embed_header()):<3} "
              f"total tokens={count_tokens(et):<4}")
        print(f"  HEADER: {c.embed_header()}")
        body = c.text[:150].replace("\n", " ")
        print(f"  BODY  : {body}...")
        print()
