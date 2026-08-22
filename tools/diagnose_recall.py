"""Why does a known-relevant chunk not surface? Locate it and report its rank per retriever.

Reranking can only reorder what stage 1 returned, so the first question is always whether
the target chunk is in the candidate pool at all.

    python tools/diagnose_recall.py "Friday congregational prayer" --contains "Congregation Day"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from rag.retrieve import Retriever


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--contains", required=True, help="substring identifying the target chunk")
    ap.add_argument("--depth", type=int, default=200)
    args = ap.parse_args()

    question = " ".join(args.question)
    r = Retriever()

    target_rows = r.conn.execute(
        "SELECT id, citation FROM chunks WHERE text LIKE ?", (f"%{args.contains}%",)
    ).fetchall()
    if not target_rows:
        print(f"no chunk contains {args.contains!r}")
        return

    targets = {int(row["id"]): row["citation"] for row in target_rows}
    print(f"target chunks containing {args.contains!r}:")
    for cid, cit in targets.items():
        print(f"  id={cid}  {cit}")

    print(f"\nQ: {question}")
    dense = r.dense_search(question, args.depth)
    lex = r.lexical_search(question, args.depth)

    dense_pos = {cid: i for i, (cid, _) in enumerate(dense, 1)}
    lex_pos = {cid: i for i, (cid, _) in enumerate(lex, 1)}

    print(f"\nsearched to depth {args.depth}: dense returned {len(dense)}, bm25 returned {len(lex)}")
    for cid, cit in targets.items():
        d = dense_pos.get(cid)
        l = lex_pos.get(cid)
        print(f"\n  {cit}")
        print(f"    dense rank : {d if d else f'NOT in top {args.depth}'}")
        print(f"    bm25 rank  : {l if l else f'NOT in top {args.depth}'}")


if __name__ == "__main__":
    main()
