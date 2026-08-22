"""Find the cheapest rewrite configuration that still produces correct rewrites.

Rewriting adds latency to every question, so reasoning effort and model choice matter more
here than raw capability.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from groq import Groq

from rag.rewrite import FEWSHOT, SYSTEM, _format_turns

HISTORY = [
    {"role": "user", "content": "Is abortion permissible in Islam?"},
    {"role": "assistant", "content": "Abortion is not permitted after implantation..."},
]
CASES = [
    ("what about for women with health risks?", True),
    ("and if the mother's life is in danger?", True),
    ("What are the conditions for Friday prayer?", False),
]

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CONFIGS = [
    ("openai/gpt-oss-20b", "none"),
    ("openai/gpt-oss-20b", "low"),
    ("openai/gpt-oss-120b", "none"),
    ("groq/compound-mini", None),
]


def run(model: str, effort: str | None, question: str) -> tuple[str, float]:
    messages = [{"role": "system", "content": SYSTEM}, *FEWSHOT]
    messages.append({
        "role": "user",
        "content": f"Conversation:\n{_format_turns(HISTORY)}\n\nLatest question: {question}",
    })
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_completion_tokens": 120,
        "stream": False,
    }
    if effort is not None:
        kwargs["reasoning_effort"] = effort
    t0 = time.perf_counter()
    out = client.chat.completions.create(**kwargs)
    dt = (time.perf_counter() - t0) * 1000
    return (out.choices[0].message.content or "").strip(), dt


for model, effort in CONFIGS:
    label = f"{model} effort={effort}"
    try:
        # Warm the connection so the first case does not absorb TLS setup.
        run(model, effort, "warmup")
        times, correct = [], 0
        for question, expect_change in CASES:
            text, dt = run(model, effort, question)
            times.append(dt)
            changed = text.lower().strip() != question.lower().strip()
            if changed == expect_change:
                correct += 1
        print(f"{label:<44} mean={sum(times)/len(times):6.0f} ms  correct={correct}/{len(CASES)}")
    except Exception as exc:
        print(f"{label:<44} FAILED: {type(exc).__name__}: {str(exc)[:90]}")
