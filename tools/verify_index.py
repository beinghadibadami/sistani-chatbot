"""Validate the built index: vector/metadata agreement, normalisation, and citations.

    python tools/verify_index.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import faiss
import numpy as np

from ingest.store import DB_PATH, INDEX_PATH


def main() -> None:
    index = faiss.read_index(INDEX_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("=== index ===")
    print(f"  vectors      : {index.ntotal}")
    print(f"  dim          : {index.d}")
    is_ip = index.metric_type == faiss.METRIC_INNER_PRODUCT
    print(f"  inner product: {is_ip}  (required for cosine on unit vectors)")

    meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta")}
    print("\n=== meta ===")
    for k, v in meta.items():
        print(f"  {k:<12} {v}")

    rows = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
    print(f"\n=== metadata ===")
    print(f"  sqlite rows  : {rows}")
    print(f"  matches index: {rows == index.ntotal}")

    # Reconstruct a sample of stored vectors and confirm they are unit length,
    # which is what makes inner-product search equal cosine similarity.
    sample = np.stack([index.reconstruct(i) for i in range(0, index.ntotal, max(1, index.ntotal // 200))])
    norms = np.linalg.norm(sample, axis=1)
    print(f"  sampled norms: min={norms.min():.6f} max={norms.max():.6f} "
          f"all_unit={np.allclose(norms, 1.0, atol=1e-3)}")

    print("\n=== per-doc ===")
    q = ("SELECT doc_id, COUNT(*) n, SUM(n_tokens) t, "
         "SUM(locator IS NOT NULL) loc FROM chunks GROUP BY doc_id ORDER BY n DESC")
    for r in conn.execute(q):
        print(f"  {r['doc_id']:<20} {r['n']:>5} chunks  {r['t']:>8,} tok  "
              f"{r['loc']:>5} with locator")

    print("\n=== sample citations ===")
    for doc in ("quran", "islamic_laws", "sistani_qna", "hajj_rituals",
                "summary_worship", "women_rules", "jurisprudence_easy"):
        r = conn.execute(
            "SELECT citation FROM chunks WHERE doc_id = ? LIMIT 1", (doc,)
        ).fetchone()
        if r:
            print(f"  {r['citation']}")

    conn.close()


if __name__ == "__main__":
    main()
