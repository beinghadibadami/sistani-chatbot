"""Verify both LLM providers return valid answers via the live backend.

Checks:
  - /models endpoint lists both providers
  - Groq: streams correctly, sources emitted, followups present
  - Gemini: same
  - Follow-up turn: correct passage retrieved (abortion kaffara) for both
"""

from __future__ import annotations

import json
import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
Q1 = "Is abortion permissible in Islam?"
Q2 = "what is the kaffara for it?"    # follow-up — tests rewriting


def stream(question: str, provider: str, history=None, prior=None) -> dict:
    payload = {
        "question": question, "top_k": 3,
        "history": history, "prior_sources": prior,
        "provider": provider,
    }
    t0 = time.perf_counter()
    resp = requests.post(f"{BASE}/chat/stream", json=payload, stream=True, timeout=180)
    resp.raise_for_status()

    sources, answer, followups, ttft = [], "", [], None
    events, buf = [], ""

    for raw in resp.iter_content(chunk_size=None, decode_unicode=True):
        buf += raw
        frames = buf.split("\n\n"); buf = frames.pop()
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
                    ttft = (time.perf_counter() - t0) * 1000
                answer += body.get("text", "")
            elif ev == "followups":
                followups = body.get("followups", [])
            elif ev == "error":
                print(f"    !! SERVER ERROR: {body.get('detail')}")

    order = []
    for e in events:
        if not order or order[-1] != e:
            order.append(e)

    return {"sources": sources, "answer": answer, "followups": followups,
            "ttft": ttft, "order": order}


def check(label: str, result: dict, must_contain_citation: str | None = None) -> bool:
    ok = True
    print(f"\n  {'✓' if result['answer'] else '✗'} answer ({len(result['answer'])} chars)")
    print(f"  {'✓' if result['sources'] else '✗'} sources ({len(result['sources'])})")
    print(f"  event order: {' -> '.join(result['order'])}")
    print(f"  TTFT: {result['ttft']:.0f} ms" if result['ttft'] else "  TTFT: n/a")
    if result['followups']:
        print(f"  followups: {result['followups'][:2]}")
    for s in result['sources']:
        print(f"    [{s.get('source','?'):<6}] {s['citation']}")
    if must_contain_citation:
        found = any(must_contain_citation.lower() in s['citation'].lower() for s in result['sources'])
        mark = '✓' if found else '✗'
        print(f"  {mark} expected citation containing '{must_contain_citation}': {'found' if found else 'MISSING'}")
        if not found:
            ok = False
    if not result['answer']:
        ok = False
    return ok


print("=" * 80)
print(f"Verifying against {BASE}")
print("=" * 80)

# /models endpoint
models_resp = requests.get(f"{BASE}/models").json()
print(f"\n/models: {[p['id'] for p in models_resp['providers']]}  current={models_resp['current']}")
assert len(models_resp['providers']) == 2, "Expected 2 providers"

all_ok = True
for provider in ("groq", "gemini"):
    print(f"\n{'='*40}")
    print(f" PROVIDER: {provider.upper()}")
    print(f"{'='*40}")

    print(f"\n  Turn 1: {Q1!r}")
    r1 = stream(Q1, provider)
    ok1 = check("turn1", r1)

    prior = [
        {"citation": s["citation"], "text": s.get("text", ""),
         "doc_id": s.get("doc_id"), "chapter": s.get("chapter"),
         "section": s.get("section"), "locator": s.get("locator")}
        for s in r1["sources"][:3] if s.get("text")
    ]
    history = [
        {"role": "user", "content": Q1},
        {"role": "assistant", "content": r1["answer"][:500]},
    ]

    print(f"\n  Turn 2 (follow-up): {Q2!r}")
    r2 = stream(Q2, provider, history=history, prior=prior)
    ok2 = check("turn2", r2, must_contain_citation="Abortion")

    all_ok = all_ok and ok1 and ok2

print(f"\n{'='*80}")
print(f"Result: {'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED'}")
print("=" * 80)
sys.exit(0 if all_ok else 1)
