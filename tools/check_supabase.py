"""Diagnose the exact Supabase RLS state by querying pg_policies."""
import os, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
import requests

url = os.getenv("SUPABASE_URL", "").rstrip("/")
key = os.getenv("SUPABASE_ANON_KEY", "")
headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# 1. Try a raw insert so we see the exact HTTP error body
r = requests.post(f"{url}/rest/v1/feedback",
    headers={**headers, "Prefer": "return=minimal"},
    json={"session_id": "test-diag-001", "question": "diag", "answer": "diag",
          "rating": 1, "citations": [], "retrieval": {}},
    timeout=15)
print(f"Insert status : {r.status_code}")
print(f"Insert body   : {r.text[:400]}")
print()

# 2. Query the policy table via the REST API (uses service role if available, else anon)
r2 = requests.get(f"{url}/rest/v1/feedback?limit=1",
    headers={**headers, "Prefer": "return=representation"}, timeout=15)
print(f"SELECT status : {r2.status_code}  (expected 200 if anon can read, 403 otherwise)")
print(f"SELECT body   : {r2.text[:200]}")
