"""List Groq models available to this key, to pick a fast one for query rewriting.

Rewriting is a trivial transformation and does not need the 120B answer model; a small
model keeps the added latency low.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
models = client.models.list()

rows = []
for m in models.data:
    rows.append((m.id, getattr(m, "context_window", None), getattr(m, "owned_by", None)))

for mid, ctx, owner in sorted(rows):
    print(f"  {mid:<52} ctx={ctx!s:<9} owner={owner}")
