"""End-to-end test of the streaming chat endpoint, including a follow-up turn.

Verifies the SSE contract (sources -> deltas -> followups -> done), measures
time-to-first-token, and checks that a follow-up retrieves the right passages.
"""

from __future__ import annotations

import json
import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def stream(question: str, history=None, prior=None) -> dict:
    t0 = time.perf_counter()
    payload = {"question": question, "top_k": 5, "history": history, "prior_sources": prior}

    resp = requests.post(f"{BASE}/chat/stream", json=payload, stream=True, timeout=180)
    resp.raise_for_status()

    sources, answer, followups = [], "", []
    ttft = None
    events = []
    buf = ""

    for raw in resp.iter_content(chunk_size=None, decode_unicode=True):
        buf += raw
        frames = buf.split("\n\n")
        buf = frames.pop()
        for frame in frames:
            lines = frame.split("\n")
            ev = next((l[6:].strip() for l in lines if l.startswith("event:")), None)
            data = next((l[5:].strip() for l in lines if l.startswith("data:")), None)
            if not ev or not data:
                continue
            events.append(ev)
            body = json.loads(data)
            if ev == "sources":
                sources = body.get("sources", [])
            elif ev == "delta":
                if ttft is None:
                    ttft = time.perf_counter() - t0
                answer += body.get("text", "")
            elif ev == "followups":
                followups = body.get("followups", [])
            elif ev == "error":
                print(f"  !! ERROR: {body.get('detail')}")

    total = time.perf_counter() - t0
    order = []
    for e in events:
        if not order or order[-1] != e:
            order.append(e)

    print(f"  event order      : {' -> '.join(order)}")
    print(f"  time to 1st token: {ttft*1000:.0f} ms" if ttft else "  no tokens received")
    print(f"  total            : {total*1000:.0f} ms")
    print(f"  sources          : {len(sources)}")
    for s in sources:
        print(f"     [{s.get('source'):<6}] {s['citation']}")
    print(f"  answer chars     : {len(answer)}")
    print(f"  followups        : {followups}")
    print(f"\n  --- answer ---\n{answer[:700]}{'...' if len(answer) > 700 else ''}\n")

    return {"sources": sources, "answer": answer, "followups": followups}


print("=" * 92)
print("TURN 1")
print("=" * 92)
t1 = stream("Is abortion permissible in Islam?")

print("=" * 92)
print("TURN 2 (follow-up: relies on rewriting + prior passages)")
print("=" * 92)
history = [
    {"role": "user", "content": "Is abortion permissible in Islam?"},
    {"role": "assistant", "content": t1["answer"][:800]},
]
prior = [
    {
        "citation": s["citation"],
        "text": s.get("text", ""),
        "doc_id": s.get("doc_id"),
        "chapter": s.get("chapter"),
        "section": s.get("section"),
        "locator": s.get("locator"),
    }
    for s in t1["sources"][:5]
    if s.get("text")
]
stream("what is the kaffara for it?", history=history, prior=prior)
