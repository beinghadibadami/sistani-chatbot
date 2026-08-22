"""Audit stored chapter/section titles for detection errors.

Citations are shown to users, so a body line misread as a heading is a visible defect.
Flags titles containing Arabic script or that are implausibly long for a heading.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.store import DB_PATH

ARABIC = re.compile(r"[\u0600-\u06FF]")
MAX_TITLE = 70


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    for field in ("chapter", "section"):
        print("=" * 90)
        print(f"AUDIT: {field}")
        print("=" * 90)
        rows = conn.execute(
            f"SELECT doc_id, {field} AS title, COUNT(*) AS n FROM chunks "
            f"WHERE {field} IS NOT NULL GROUP BY doc_id, {field}"
        ).fetchall()
        print(f"  distinct values: {len(rows)}")
        bad = [
            r for r in rows
            if ARABIC.search(r["title"]) or len(r["title"]) > MAX_TITLE
        ]
        print(f"  suspicious     : {len(bad)}")
        for r in sorted(bad, key=lambda r: -r["n"]):
            flag = "arabic" if ARABIC.search(r["title"]) else "long"
            print(f"    [{flag:<6}] {r['doc_id']:<16} n={r['n']:<4} len={len(r['title']):<4} "
                  f"{r['title'][:90]!r}")

    conn.close()


if __name__ == "__main__":
    main()
