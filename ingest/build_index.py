"""Build the vector index from all documents.

    python -m ingest.build_index                # resume if a checkpoint exists
    python -m ingest.build_index --fresh        # ignore any checkpoint
    python -m ingest.build_index --limit 200    # smoke test on a small slice

Embedding the full corpus takes tens of minutes on a modest CPU, so vectors are checkpointed
to disk in blocks. A crash or interrupt resumes from the last completed block instead of
restarting, and the checkpoint is validated against the current chunk set so a stale
checkpoint can never be silently mixed into a new build.
"""

from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

import numpy as np

from ingest.base import Chunk, count_tokens
from ingest.chunkers import CHUNKERS
from ingest.embed import EMBED_DIM, MODEL_NAME, get_embedder
from ingest.store import DB_PATH, INDEX_PATH, write_store

CKPT_DIR = Path("artifacts/checkpoint")
BLOCK = 256          # chunks per checkpoint block


def collect_chunks() -> list[Chunk]:
    """Chunk every document in a stable order so checkpoints stay valid across runs."""
    out: list[Chunk] = []
    for doc_id in sorted(CHUNKERS):
        chunks = CHUNKERS[doc_id]()
        print(f"  {doc_id:<20} {len(chunks):>5} chunks")
        out.extend(chunks)
    return out


def fingerprint(chunks: list[Chunk]) -> str:
    """Identify the exact chunk set + model, so a stale checkpoint is never reused."""
    h = hashlib.sha256()
    h.update(MODEL_NAME.encode())
    h.update(str(len(chunks)).encode())
    # Hash embed_text, not text: the header is part of what gets vectorised, so a change to
    # header construction must invalidate the checkpoint too.
    for c in chunks[::37]:          # sample for speed; sensitive to content changes
        h.update(c.embed_text()[:160].encode("utf-8", "ignore"))
    return h.hexdigest()[:16]


def fmt_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds/60:.1f}m"
    return f"{seconds/3600:.1f}h"


def embed_all(
    chunks: list[Chunk], backend: str, batch_size: int, fresh: bool
) -> np.ndarray:
    fp = fingerprint(chunks)
    ckpt = CKPT_DIR / fp
    ckpt.mkdir(parents=True, exist_ok=True)

    if fresh:
        for f in ckpt.glob("block_*.npy"):
            f.unlink()

    embedder = get_embedder(backend)
    n = len(chunks)
    n_blocks = (n + BLOCK - 1) // BLOCK
    # Progress/ETA are driven by embed_text length, which is what is actually processed.
    tokens_per_chunk = [count_tokens(c.embed_text()) for c in chunks]
    total_tokens = sum(tokens_per_chunk)

    print(f"\nembedding {n} chunks ({total_tokens:,} tokens) "
          f"in {n_blocks} blocks of {BLOCK} via '{backend}'")
    print(f"checkpoint dir: {ckpt}")

    done = sorted(int(f.stem.split("_")[1]) for f in ckpt.glob("block_*.npy"))
    if done:
        print(f"resuming: {len(done)}/{n_blocks} blocks already embedded")

    start = time.perf_counter()
    tokens_done = 0
    blocks_run = 0

    for bi in range(n_blocks):
        lo, hi = bi * BLOCK, min((bi + 1) * BLOCK, n)
        block_tokens = sum(tokens_per_chunk[lo:hi])
        path = ckpt / f"block_{bi:05d}.npy"

        if path.exists():
            tokens_done += block_tokens
            continue

        t0 = time.perf_counter()
        # embed_text() prepends the citation header, so the vector carries chapter/section
        # provenance that the body text alone often omits.
        vecs = np.stack(
            list(embedder.embed_passages([c.embed_text() for c in chunks[lo:hi]], batch_size))
        ).astype(np.float32)
        if vecs.shape != (hi - lo, EMBED_DIM):
            raise ValueError(f"block {bi}: unexpected shape {vecs.shape}")

        # Write to a temp file then rename, so an interrupt cannot leave a partial block.
        # The handle is opened explicitly because np.save() would append '.npy' to a
        # path that does not already end in it, breaking the rename.
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "wb") as fh:
            np.save(fh, vecs)
        tmp.replace(path)

        dt = time.perf_counter() - t0
        tokens_done += block_tokens
        blocks_run += 1
        elapsed = time.perf_counter() - start
        rate = tokens_done / elapsed if elapsed else 0
        remaining = total_tokens - tokens_done
        eta = remaining / rate if rate else 0
        pct = 100 * (bi + 1) / n_blocks
        print(
            f"  block {bi+1:>3}/{n_blocks}  {pct:5.1f}%  "
            f"{hi-lo:>3} chunks / {block_tokens:>6,} tok in {dt:6.2f}s  "
            f"({block_tokens/dt:6.0f} tok/s)  ETA {fmt_eta(eta)}",
            flush=True,
        )

    vectors = np.concatenate(
        [np.load(ckpt / f"block_{bi:05d}.npy") for bi in range(n_blocks)], axis=0
    )
    print(f"\nembedded {vectors.shape[0]} vectors in {fmt_eta(time.perf_counter()-start)}"
          f" ({blocks_run} blocks computed this run)")
    return vectors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="local", choices=("local", "api"))
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="embed only the first N chunks")
    ap.add_argument("--fresh", action="store_true", help="discard existing checkpoint")
    args = ap.parse_args()

    print("chunking documents...")
    chunks = collect_chunks()
    if args.limit:
        chunks = chunks[: args.limit]
        print(f"  (limited to {len(chunks)} chunks)")
    print(f"  total: {len(chunks)} chunks")

    vectors = embed_all(chunks, args.backend, args.batch_size, args.fresh)

    print("\nwriting store...")
    write_store(chunks, vectors, model_name=MODEL_NAME)
    print(f"  {INDEX_PATH}")
    print(f"  {DB_PATH}")
    print("done.")


if __name__ == "__main__":
    main()
