"""Verify the numbered-marker chunkers dropped nothing.

For each document with sequential markers, compare the marker numbers found in the chunk
metadata against the markers present in the raw PDF text. A gap means the parser silently
lost content, which stats alone would not reveal.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

from ingest.chunkers import CHUNKERS
from ingest.chunkers.numbered import SPECS

CHECKS = {
    "islamic_laws": (re.compile(r"\bRuling\s+(\d+)\."), "Ruling"),
    "summary_worship": (re.compile(r"\bIssue\s+(\d+):"), "Issue"),
    "hajj_rituals": (re.compile(r"\bRule\s+(\d+):"), "Rule"),
}


def raw_markers(path: str, pattern: re.Pattern, start_page: int) -> set[int]:
    doc = fitz.open(path)
    found: set[int] = set()
    for pno in range(start_page, doc.page_count):
        for m in pattern.finditer(doc[pno].get_text("text")):
            found.add(int(m.group(1)))
    doc.close()
    return found


def main() -> None:
    for doc_id, (pattern, word) in CHECKS.items():
        spec = SPECS[doc_id]
        chunks = CHUNKERS[doc_id]()
        got = {
            int(c.locator.split()[-1])
            for c in chunks
            if c.locator and c.locator.startswith(word)
        }
        expected = raw_markers(spec.path, pattern, spec.start_page)

        missing = sorted(expected - got)
        extra = sorted(got - expected)
        print("=" * 80)
        print(f"{doc_id}: {word} markers")
        print(f"  in raw PDF     : {len(expected)}  (range {min(expected)}..{max(expected)})")
        print(f"  in chunks      : {len(got)}")
        print(f"  missing        : {len(missing)} {missing[:15]}{'...' if len(missing) > 15 else ''}")
        print(f"  unexpected     : {len(extra)} {extra[:15]}{'...' if len(extra) > 15 else ''}")

        # Gaps in the expected sequence indicate cross-reference-only numbers, not losses.
        seq_gaps = [n for n in range(min(expected), max(expected) + 1) if n not in expected]
        if seq_gaps:
            print(f"  (numbers absent from raw text: {len(seq_gaps)} {seq_gaps[:10]})")

    for doc_id in ("women_rules", "jurisprudence_easy", "quran", "sistani_qna"):
        chunks = CHUNKERS[doc_id]()
        chapters = {c.chapter for c in chunks if c.chapter}
        sections = {c.section for c in chunks if c.section}
        print("=" * 80)
        print(f"{doc_id}: {len(chunks)} chunks, "
              f"{len(chapters)} chapters, {len(sections)} sections, "
              f"{sum(1 for c in chunks if not c.chapter)} chunks lacking a chapter")


if __name__ == "__main__":
    main()
