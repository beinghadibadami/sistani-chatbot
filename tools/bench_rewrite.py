"""Measure query-rewrite latency and correctness on follow-up vs standalone questions."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from rag.rewrite import REWRITE_MODEL, rewrite_query

HISTORY = [
    {"role": "user", "content": "Is abortion permissible in Islam?"},
    {
        "role": "assistant",
        "content": (
            "Abortion is not permitted after implantation of the fertilised ovum, except "
            "where the mother's life is in danger, in which case it is permissible before "
            "the soul enters the foetus."
        ),
    },
]

CASES = [
    ("what about for women with health risks?", True),
    ("and if the mother's life is in danger?", True),
    ("is it allowed after four months?", True),
    ("What are the conditions for Friday prayer?", False),
    ("How is wudu performed?", False),
]

print(f"rewrite model: {REWRITE_MODEL}\n")

total = 0.0
for question, expect_rewrite in CASES:
    t0 = time.perf_counter()
    rewritten, changed = rewrite_query(question, HISTORY)
    dt = (time.perf_counter() - t0) * 1000
    total += dt
    ok = "OK " if changed == expect_rewrite else "!! "
    print(f"{ok} {dt:6.0f} ms  changed={str(changed):<5} expect={expect_rewrite}")
    print(f"      in : {question}")
    print(f"      out: {rewritten}")

print(f"\nmean latency: {total/len(CASES):.0f} ms")
