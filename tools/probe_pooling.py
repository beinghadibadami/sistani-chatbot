"""Decide whether HF-API vectors are interchangeable with fastembed vectors.

Index documents are embedded locally (fastembed, CLS pooling). If production must embed
queries via the HF API instead, the API vectors have to land in the SAME space, otherwise
retrieval silently returns noise. This compares the candidate poolings against fastembed.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import requests
from dotenv import load_dotenv
from fastembed import TextEmbedding

load_dotenv()

MODEL = "BAAI/bge-small-en-v1.5"
HF_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL}/pipeline/feature-extraction"
HF_TOKEN = os.getenv("HF_TOKEN")

TEXTS = [
    "Is abortion permissible in Islam?",
    "Ruling 2748. If there is only one heir of the deceased from the first group, "
    "then that person inherits the deceased's entire estate.",
]


def cos(a, b):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main() -> None:
    if not HF_TOKEN:
        print("HF_TOKEN not set; cannot run the API side of this comparison.")
        return

    emb = TextEmbedding(model_name=MODEL)
    local = [np.asarray(v) for v in emb.embed(TEXTS)]

    for text, lv in zip(TEXTS, local):
        resp = requests.post(
            HF_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": text},
            timeout=60,
        )
        print("=" * 78)
        print(f"text: {text[:60]}...")
        print(f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            print(f"  body: {resp.text[:300]}")
            continue

        data = resp.json()
        arr = np.array(data, dtype=np.float32)
        print(f"  API response shape: {arr.shape}")
        print(f"  fastembed dim     : {lv.shape}, norm={np.linalg.norm(lv):.4f}")

        if arr.ndim == 3:
            arr = arr[0]
        if arr.ndim == 2:
            # Candidate poolings over token-level output.
            cls_vec = arr[0]
            mean_vec = arr.mean(axis=0)
            print(f"  cos(fastembed, API CLS-pooled ) = {cos(lv, cls_vec):.6f}")
            print(f"  cos(fastembed, API mean-pooled) = {cos(lv, mean_vec):.6f}")
        else:
            print(f"  API returned a single pooled vector, norm={np.linalg.norm(arr):.4f}")
            print(f"  cos(fastembed, API pooled)      = {cos(lv, arr):.6f}")


if __name__ == "__main__":
    main()
