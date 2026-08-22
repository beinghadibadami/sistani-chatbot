"""End-to-end check that follow-up questions retrieve the right passages.

Compares, for a real follow-up, what retrieval finds with and without query rewriting, and
whether the previous turn's passages (the carry-forward mechanism) would have covered it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from rag.retrieve import Retriever
from rag.rewrite import REWRITE_ENABLED, rewrite_query

TURN1 = "Is abortion permissible in Islam?"
FOLLOWUPS = [
    "what is the kaffara for it?",
    "what about for women with health risks?",
    "is it allowed after four months?",
]

r = Retriever(backend="local")
print(f"rewrite enabled: {REWRITE_ENABLED}\n")

turn1_hits = r.search(TURN1, k=5)
turn1_citations = {h.citation for h in turn1_hits}
print(f"TURN 1: {TURN1}")
for h in turn1_hits:
    print(f"   {h.citation}")

answer1 = "Abortion is not permitted after implantation except where the mother's life is at risk."
history = [
    {"role": "user", "content": TURN1},
    {"role": "assistant", "content": answer1},
]

for followup in FOLLOWUPS:
    print("\n" + "=" * 94)
    print(f"FOLLOW-UP: {followup}")
    print("=" * 94)

    raw = r.search(followup, k=3)
    print("  without rewriting:")
    for h in raw:
        print(f"     {h.citation}")

    t0 = time.perf_counter()
    rewritten, changed = rewrite_query(followup, history)
    dt = (time.perf_counter() - t0) * 1000

    print(f"\n  rewritten ({dt:.0f} ms, changed={changed}): {rewritten}")
    fixed = r.search(rewritten, k=3)
    print("  with rewriting:")
    for h in fixed:
        print(f"     {h.citation}")

    # Would replaying the previous turn's passages have covered this follow-up?
    gained = [h.citation for h in fixed if h.citation not in turn1_citations]
    print(f"\n  passages rewriting found that turn 1 did NOT have: {len(gained)}")
    for c in gained:
        print(f"     + {c}")
