"""Inspect chunker output per document: stats, cap violations, and sample chunks.

Usage:
  python test_chunkers.py                 # all docs, summary stats
  python test_chunkers.py islamic_laws    # one doc, with sample chunks
  python test_chunkers.py islamic_laws --find "Ruling 2748"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.base import TOKEN_CAPS
from ingest.chunkers import CHUNKERS


def stats(doc_id: str, chunks: list) -> dict:
    cap = TOKEN_CAPS[doc_id]
    toks = [c.n_tokens for c in chunks]
    over = [c for c in chunks if c.n_tokens > cap]
    no_chapter = [c for c in chunks if not c.chapter]
    no_locator = [c for c in chunks if not c.locator]
    return {
        "chunks": len(chunks),
        "cap": cap,
        "tok_min": min(toks) if toks else 0,
        "tok_max": max(toks) if toks else 0,
        "tok_mean": round(sum(toks) / len(toks), 1) if toks else 0,
        "over_cap": len(over),
        "missing_chapter": len(no_chapter),
        "missing_locator": len(no_locator),
    }


def show(chunks: list, idxs: list[int]) -> None:
    for i in idxs:
        if i >= len(chunks):
            continue
        c = chunks[i]
        print("-" * 90)
        print(f"[{i}] tokens={c.n_tokens}")
        print(f"  citation: {c.citation()}")
        print(f"  chapter : {c.chapter}")
        print(f"  section : {c.section}")
        print(f"  locator : {c.locator}")
        if c.extra:
            print(f"  extra   : {c.extra}")
        body = c.text if len(c.text) < 700 else c.text[:700] + " ...[trunc]"
        print(f"  text    : {body}")


def main() -> None:
    argv = sys.argv[1:]
    find = None
    if "--find" in argv:
        i = argv.index("--find")
        find = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")]

    targets = args or list(CHUNKERS)
    for doc_id in targets:
        print("=" * 90)
        print(f"DOC: {doc_id}")
        print("=" * 90)
        try:
            chunks = CHUNKERS[doc_id]()
        except Exception as exc:  # noqa: BLE001 - surface any parser failure per doc
            print(f"  !! FAILED: {type(exc).__name__}: {exc}")
            import traceback

            traceback.print_exc()
            continue
        s = stats(doc_id, chunks)
        for k, v in s.items():
            print(f"  {k:<18} {v}")

        if find:
            hits = [i for i, c in enumerate(chunks) if find.lower() in (c.locator or "").lower()]
            print(f"\n  matches for locator ~ {find!r}: {hits[:10]}")
            show(chunks, hits[:4])
        elif args:
            n = len(chunks)
            show(chunks, [0, 1, n // 3, n // 2, n - 1])
        print()


if __name__ == "__main__":
    main()
