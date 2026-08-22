"""Embedding backends for BGE, with the query/passage asymmetry handled correctly.

Two backends produce interchangeable vectors (verified cosine ~0.999999 on identical text):

  local : fastembed + ONNX Runtime, no PyTorch. Used to build the index, because it has no
          rate limits and no per-call network cost.
  api   : HuggingFace Inference API. Used in production, where a 512 MB / 0.1 CPU host
          cannot afford to hold an ONNX model in memory or spend seconds per inference.

Both return L2-normalised vectors, so a FAISS inner-product index yields exact cosine
similarity without further normalisation.

BGE retrieval is asymmetric: the *query* must be prefixed with an instruction while
passages must not. fastembed's `query_embed()` does NOT apply this prefix (it is identical
to `embed()`), so it is applied explicitly here. Omitting it measurably degrades retrieval.
"""

from __future__ import annotations

import os
from typing import Iterable, Iterator, Protocol

import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384

# Prescribed by the BGE authors for retrieval queries; passages get no prefix.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

HF_API_URL = (
    f"https://router.huggingface.co/hf-inference/models/{MODEL_NAME}"
    "/pipeline/feature-extraction"
)


class Embedder(Protocol):
    def embed_passages(self, texts: Iterable[str], batch_size: int = 32) -> Iterator[np.ndarray]: ...
    def embed_query(self, text: str) -> np.ndarray: ...


def _as_unit(vec: np.ndarray) -> np.ndarray:
    """Return a float32 unit vector, guarding against a non-normalised backend."""
    vec = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(vec))
    if norm > 0 and abs(norm - 1.0) > 1e-3:
        vec = vec / norm
    return vec


class LocalEmbedder:
    """fastembed/ONNX backend. Model is loaded lazily so importing this module stays cheap."""

    def __init__(self, model_name: str = MODEL_NAME, threads: int | None = None):
        self.model_name = model_name
        self._threads = threads
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from fastembed import TextEmbedding

            kwargs = {} if self._threads is None else {"threads": self._threads}
            self._model = TextEmbedding(model_name=self.model_name, **kwargs)
        return self._model

    def embed_passages(
        self, texts: Iterable[str], batch_size: int = 32
    ) -> Iterator[np.ndarray]:
        for vec in self.model.embed(list(texts), batch_size=batch_size):
            yield _as_unit(vec)

    def embed_query(self, text: str) -> np.ndarray:
        vec = next(iter(self.model.embed([QUERY_PREFIX + text])))
        return _as_unit(vec)


class ApiEmbedder:
    """HuggingFace Inference API backend, for hosts too small to run ONNX locally."""

    def __init__(self, token: str | None = None, timeout: float = 30.0, retries: int = 3):
        self.token = token or os.getenv("HF_TOKEN")
        if not self.token:
            raise RuntimeError("HF_TOKEN is not set; ApiEmbedder cannot authenticate.")
        self.timeout = timeout
        self.retries = retries
        self._session = None

    @property
    def session(self):
        if self._session is None:
            import requests

            self._session = requests.Session()
            self._session.headers.update({"Authorization": f"Bearer {self.token}"})
        return self._session

    def _post(self, text: str) -> np.ndarray:
        import requests

        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                resp = self.session.post(
                    HF_API_URL, json={"inputs": text}, timeout=self.timeout
                )
                resp.raise_for_status()
                arr = np.array(resp.json(), dtype=np.float32)
                if arr.ndim == 3:
                    arr = arr[0]
                if arr.ndim == 2:
                    # Token-level output: BGE uses CLS pooling, i.e. the first token.
                    arr = arr[0]
                if arr.shape != (EMBED_DIM,):
                    raise ValueError(f"unexpected embedding shape {arr.shape}")
                return _as_unit(arr)
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt < self.retries - 1:
                    import time

                    time.sleep(2**attempt)
        raise RuntimeError(f"HF embedding failed after {self.retries} attempts: {last_exc}")

    def embed_passages(
        self, texts: Iterable[str], batch_size: int = 32
    ) -> Iterator[np.ndarray]:
        for text in texts:
            yield self._post(text)

    def embed_query(self, text: str) -> np.ndarray:
        return self._post(QUERY_PREFIX + text)


def get_embedder(backend: str = "local", **kwargs) -> Embedder:
    if backend == "local":
        return LocalEmbedder(**kwargs)
    if backend == "api":
        return ApiEmbedder(**kwargs)
    raise ValueError(f"unknown embedding backend: {backend!r}")
