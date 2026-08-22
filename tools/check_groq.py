"""Verify the configured Groq model is reachable and measure streaming latency.

Confirms the migration target works before the app depends on it, and reports
time-to-first-token, which is what the user actually perceives.
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

from rag.generate import GROQ_MODEL, REASONING_EFFORT

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

print(f"model: {GROQ_MODEL}  reasoning_effort={REASONING_EFFORT}")

messages = [
    {"role": "system", "content": "You are a concise Islamic jurisprudence assistant."},
    {"role": "user", "content": "In two sentences, what is taqlid?"},
]

kwargs = {
    "model": GROQ_MODEL,
    "messages": messages,
    "temperature": 0,
    "max_completion_tokens": 300,
    "stream": True,
}
if "gpt-oss" in GROQ_MODEL:
    kwargs["reasoning_effort"] = REASONING_EFFORT

t0 = time.perf_counter()
ttft = None
pieces = []
for chunk in client.chat.completions.create(**kwargs):
    if not chunk.choices:
        continue
    piece = chunk.choices[0].delta.content
    if piece:
        if ttft is None:
            ttft = time.perf_counter() - t0
        pieces.append(piece)

total = time.perf_counter() - t0
text = "".join(pieces)
print(f"\ntime to first token : {ttft*1000:.0f} ms" if ttft else "\nno content received")
print(f"total stream time   : {total*1000:.0f} ms")
print(f"chars               : {len(text)}")
print(f"\n{text}")
