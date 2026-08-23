"""Verify that DEFAULT_TOP_K=3 works and sources are capped properly."""
import requests

r = requests.post("http://localhost:8000/chat",
                  json={"question": "What is wudu?"}, timeout=60)
d = r.json()
print(f"top_k: {d['top_k']}")
print(f"sources: {len(d['sources'])}")
for s in d["sources"]:
    print(f"  {s['citation'][:80]}")
