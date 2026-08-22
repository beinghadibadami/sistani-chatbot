"""Shared, cached Groq clients.

Constructing a Groq client per request forces a fresh TLS handshake, which measured ~1000ms
of pure overhead on every call (rewrite latency dropped from ~1390ms to ~360ms once the
connection was reused). Clients are therefore created once and shared.
"""

from __future__ import annotations

import os
import threading
from typing import Any

_lock = threading.Lock()
_clients: dict[float, Any] = {}


def get_client(timeout: float = 30.0):
    """Return a process-wide Groq client for the given timeout."""
    client = _clients.get(timeout)
    if client is not None:
        return client
    with _lock:
        client = _clients.get(timeout)
        if client is None:
            from groq import Groq

            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is not set.")
            client = Groq(api_key=api_key, timeout=timeout)
            _clients[timeout] = client
    return client
