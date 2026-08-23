"""Verify greeting handling, off-topic decline, and source suppression on decline."""
import requests

BASE = "http://localhost:8000"


def ask(q, label):
    r = requests.post(f"{BASE}/chat", json={"question": q, "top_k": 5}, timeout=60)
    d = r.json()
    print(f"[{label}] {q!r}")
    print(f"  answer : {d['answer'][:150]}")
    print(f"  sources: {len(d['sources'])}")
    print()


ask("as salam how are u", "greeting")
ask("what is your favorite football team", "off-topic")
ask("What is wudu?", "real question")
