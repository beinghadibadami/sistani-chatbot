"""Verify Quran chunking completeness: surah coverage and verse continuity.

Checks against the known verse counts of all 114 surahs, which is the strongest available
signal that extraction lost nothing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.chunkers.quran import chunk_quran

# Canonical verse counts per surah (1-114).
EXPECTED = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110,
    98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88,
    75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24,
    13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42,
    29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3,
    9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
]


def main() -> None:
    chunks = chunk_quran()
    print(f"total chunks: {len(chunks)}")

    by_surah: dict[int, set[int]] = {}
    for c in chunks:
        s = c.extra.get("surah")
        if s is None:
            continue
        rng = range(c.extra["verse_start"], c.extra["verse_end"] + 1)
        by_surah.setdefault(s, set()).update(rng)

    print(f"surahs found: {len(by_surah)} (expected 114)")
    missing_surahs = [s for s in range(1, 115) if s not in by_surah]
    if missing_surahs:
        print(f"  !! MISSING SURAHS: {missing_surahs}")

    problems = 0
    for s in range(1, 115):
        if s not in by_surah:
            continue
        got = by_surah[s]
        exp = EXPECTED[s - 1]
        expected_set = set(range(1, exp + 1))
        missing = sorted(expected_set - got)
        extra = sorted(got - expected_set)
        if missing or extra:
            problems += 1
            print(f"  surah {s:>3}: expected 1..{exp}, max_seen={max(got)}"
                  f" missing={missing[:8]}{'...' if len(missing) > 8 else ''}"
                  f" extra={extra[:8]}{'...' if len(extra) > 8 else ''}")

    print(f"\nsurahs with verse-coverage problems: {problems}/114")

    # Spot-check the surah used as a worked example during design.
    print("\n--- Surah 62 chunks ---")
    for c in chunks:
        if c.extra.get("surah") == 62:
            print(f"  {c.citation()}  ({c.n_tokens} tok)")
            print(f"    {c.text[:200]}...")


if __name__ == "__main__":
    main()
