"""Groq client pool with automatic key rotation on rate limits.

Supports multiple API keys in GROQ_API_KEY separated by commas:
    GROQ_API_KEY=key1,key2,key3

When a key hits a rate limit (429) or auth error (401), the pool rotates to the next key
automatically. This is transparent to callers — they just call get_client() and the pool
handles failover internally.

TLS connection reuse is preserved per key: each key gets its own cached Groq client so the
handshake cost (~1s) is paid only once per key per process lifetime.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()


class GroqPool:
    """Round-robin pool of Groq clients, one per API key."""

    def __init__(self):
        raw = os.getenv("GROQ_API_KEY", "")
        self._keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not self._keys:
            raise RuntimeError("GROQ_API_KEY is not set or empty.")
        self._index = 0
        # One client per (key, timeout) pair — preserves TLS reuse.
        self._clients: dict[tuple[int, float], Any] = {}
        # Track which keys are temporarily exhausted and when they can be retried.
        self._cooldowns: dict[int, float] = {}
        logger.info(f"Groq pool initialized with {len(self._keys)} key(s)")

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def _get_or_create(self, key_idx: int, timeout: float):
        cache_key = (key_idx, timeout)
        client = self._clients.get(cache_key)
        if client is None:
            from groq import Groq
            client = Groq(api_key=self._keys[key_idx], timeout=timeout)
            self._clients[cache_key] = client
        return client

    def _next_available(self) -> int:
        """Find the next key that isn't in cooldown. Wraps around."""
        now = time.time()
        n = len(self._keys)
        for offset in range(n):
            idx = (self._index + offset) % n
            cooldown_until = self._cooldowns.get(idx, 0)
            if now >= cooldown_until:
                return idx
        # All keys in cooldown — use the one closest to expiring.
        earliest = min(self._cooldowns, key=lambda k: self._cooldowns[k])
        return earliest

    def get_client(self, timeout: float = 30.0):
        """Get the current active client."""
        with _lock:
            idx = self._next_available()
            self._index = idx
            return self._get_or_create(idx, timeout)

    def mark_failed(self, cooldown_seconds: float = 60.0):
        """Mark the current key as rate-limited; rotate to the next one.

        Called when a 429/rate-limit error is caught. The failed key enters a cooldown
        period and won't be used again until it expires.
        """
        with _lock:
            failed_idx = self._index
            self._cooldowns[failed_idx] = time.time() + cooldown_seconds
            self._index = (failed_idx + 1) % len(self._keys)
            remaining = sum(
                1 for i in range(len(self._keys))
                if time.time() >= self._cooldowns.get(i, 0)
            )
            logger.warning(
                f"Groq key #{failed_idx + 1} rate-limited, rotating. "
                f"{remaining}/{len(self._keys)} keys available."
            )


_pool: GroqPool | None = None


def _get_pool() -> GroqPool:
    global _pool
    if _pool is None:
        with _lock:
            if _pool is None:
                _pool = GroqPool()
    return _pool


def get_client(timeout: float = 30.0):
    """Return the current active Groq client from the pool."""
    return _get_pool().get_client(timeout)


def mark_rate_limited(cooldown: float = 60.0):
    """Call this when a Groq API call returns 429. Rotates to the next key."""
    _get_pool().mark_failed(cooldown)


def get_pool_status() -> dict:
    """Status info for health/debug endpoints."""
    pool = _get_pool()
    now = time.time()
    return {
        "total_keys": pool.key_count,
        "active_key_index": pool._index + 1,
        "keys_available": sum(
            1 for i in range(pool.key_count)
            if now >= pool._cooldowns.get(i, 0)
        ),
    }
