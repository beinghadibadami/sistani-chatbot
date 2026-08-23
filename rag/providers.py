"""LLM provider abstraction — Groq and Gemini with a shared streaming interface.

Both providers yield ``("delta", text)`` and optionally ``("followups", [...])`` tuples,
so the streaming parser in generate.py works identically regardless of the backend.

Provider selection:
  - env LLM_PROVIDER = "groq" (default) | "gemini"
  - can be overridden per-request by passing provider= to generate() / stream_generate()
  - in local dev the UI exposes a model switcher; in production only the env var applies

Models:
  Groq    openai/gpt-oss-120b  — fastest TTFT on the platform (~500 tok/s LPU hardware)
  Gemini  gemini-2.0-flash-001 — free tier, 1M context, stronger reasoning
"""

from __future__ import annotations

import os
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def default_provider() -> str:
    return os.getenv("LLM_PROVIDER", "groq").lower()


AVAILABLE_PROVIDERS = {
    "groq": {
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "label": "Groq · gpt-oss-120b",
        "notes": "Fastest TTFT; free tier with rate limits",
    },
    "gemini": {
        "model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        "label": "Gemini · gemini-3.6-flash",
        "notes": "Free tier; 1M context; stronger reasoning",
    },
}


# ---------------------------------------------------------------------------
# Groq provider
# ---------------------------------------------------------------------------

GROQ_MODELS = [
    os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
]


def _groq_kwargs(messages: list[dict], stream: bool, max_tokens: int,
                 temperature: float, reasoning_effort: str, model: str | None = None) -> dict:
    m = model or GROQ_MODELS[0]
    kw = {
        "model": m,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "top_p": 1,
        "stream": stream,
    }
    if "gpt-oss" in m and reasoning_effort:
        kw["reasoning_effort"] = reasoning_effort
    return kw


def groq_generate(messages: list[dict], *, max_tokens: int, temperature: float,
                  reasoning_effort: str) -> str:
    from rag.groq_client import get_client, mark_rate_limited
    
    # Try each model on each key rotation — 3 keys × 3 models = 9 attempts max
    for attempt in range(len(GROQ_MODELS) * 3):
        model = GROQ_MODELS[attempt % len(GROQ_MODELS)]
        kw = _groq_kwargs(messages, stream=False, max_tokens=max_tokens,
                          temperature=temperature, reasoning_effort=reasoning_effort,
                          model=model)
        try:
            c = get_client().chat.completions.create(**kw)
            return c.choices[0].message.content or ""
        except Exception as exc:
            if _is_rate_limit(exc):
                mark_rate_limited()
                continue
            raise
    raise RuntimeError("All Groq API keys and models are rate-limited. Please try again shortly.")


def groq_stream(messages: list[dict], *, max_tokens: int, temperature: float,
                reasoning_effort: str) -> Iterator[str]:
    from rag.groq_client import get_client, mark_rate_limited

    for attempt in range(len(GROQ_MODELS) * 3):
        model = GROQ_MODELS[attempt % len(GROQ_MODELS)]
        kw = _groq_kwargs(messages, stream=True, max_tokens=max_tokens,
                          temperature=temperature, reasoning_effort=reasoning_effort,
                          model=model)
        try:
            for chunk in get_client().chat.completions.create(**kw):
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as exc:
            if _is_rate_limit(exc):
                mark_rate_limited()
                continue
            raise
    raise RuntimeError("All Groq API keys and models are rate-limited. Please try again shortly.")


def _is_rate_limit(exc: Exception) -> bool:
    """Check if an exception is a rate-limit (429/503) or auth (401) error."""
    exc_str = str(exc).lower()
    # Groq rate limit
    if "429" in exc_str or "rate" in exc_str or "rate_limit" in exc_str:
        return True
    # Gemini rate limit (503 or quota exceeded)
    if "503" in exc_str or "quota" in exc_str or "resource_exhausted" in exc_str:
        return True
    # Invalid/revoked key
    if "401" in exc_str or "authentication" in exc_str or "api_key" in exc_str:
        return True
    return False


# ---------------------------------------------------------------------------
# Gemini provider (with key rotation similar to Groq)
# ---------------------------------------------------------------------------

_gemini_key_index = 0
_gemini_keys: list[str] = []


def _load_gemini_keys():
    """Load all Gemini API keys from GEMINI_API_KEY env (comma/space separated)."""
    global _gemini_keys
    if _gemini_keys:
        return _gemini_keys
    
    raw = os.getenv("GEMINI_API_KEY", "")
    if not raw:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    
    _gemini_keys = [k.strip() for k in raw.replace(",", " ").split() if k.strip()]
    if not _gemini_keys:
        raise RuntimeError("GEMINI_API_KEY is empty.")
    
    return _gemini_keys


def _gemini_client():
    """Get Gemini client with the current key from rotation."""
    from google import genai
    keys = _load_gemini_keys()
    key = keys[_gemini_key_index % len(keys)]
    return genai.Client(api_key=key)


def _rotate_gemini_key():
    """Move to the next Gemini API key in rotation."""
    global _gemini_key_index
    keys = _load_gemini_keys()
    _gemini_key_index = (_gemini_key_index + 1) % len(keys)
    print(f"[providers] Rotated to Gemini key {_gemini_key_index + 1}/{len(keys)}")


def _to_gemini_contents(messages: list[dict]) -> tuple[str | None, list[Any]]:
    """Convert OpenAI-style messages to Gemini's system_instruction + contents format.

    Gemini uses a different turn structure:
      - system messages → single system_instruction string
      - user/assistant turns → list of Content objects
    Multiple system messages are concatenated, which is how the context blocks work.
    """
    from google.genai import types

    system_parts: list[str] = []
    contents: list[Any] = []

    for msg in messages:
        role = msg.get("role", "")
        text = (msg.get("content") or "").strip()
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
        elif role == "user":
            contents.append(types.Content(role="user",
                parts=[types.Part(text=text)]))
        elif role == "assistant":
            contents.append(types.Content(role="model",
                parts=[types.Part(text=text)]))

    system_instruction = "\n\n---\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents


def _gemini_model() -> str:
    """Use env var if set, otherwise the value registered in AVAILABLE_PROVIDERS."""
    return os.getenv("GEMINI_MODEL") or AVAILABLE_PROVIDERS["gemini"]["model"]


def gemini_generate(messages: list[dict], *, max_tokens: int, temperature: float,
                    **_: Any) -> str:
    from google.genai import types
    keys = _load_gemini_keys()
    model = _gemini_model()
    system_instruction, contents = _to_gemini_contents(messages)

    cfg = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
    )
    
    # Try each Gemini key (rotate on rate limit)
    for attempt in range(len(keys)):
        client = _gemini_client()
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=cfg)
            return resp.text or ""
        except Exception as e:
            if _is_rate_limit(e) and attempt < len(keys) - 1:
                _rotate_gemini_key()
                continue
            raise  # Last key or non-rate-limit error


def gemini_stream(messages: list[dict], *, max_tokens: int, temperature: float,
                  **_: Any) -> Iterator[str]:
    from google.genai import types
    keys = _load_gemini_keys()
    model = _gemini_model()
    system_instruction, contents = _to_gemini_contents(messages)

    cfg = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
    )
    
    # Try each Gemini key (rotate on rate limit)
    for attempt in range(len(keys)):
        client = _gemini_client()
        try:
            for chunk in client.models.generate_content_stream(
                model=model, contents=contents, config=cfg
            ):
                if chunk.text:
                    yield chunk.text
            return  # Success, exit
        except Exception as e:
            if _is_rate_limit(e) and attempt < len(keys) - 1:
                _rotate_gemini_key()
                continue
            raise  # Last key or non-rate-limit error


# ---------------------------------------------------------------------------
# Unified dispatch
# ---------------------------------------------------------------------------

def call_generate(messages: list[dict], provider: str | None, *,
                  max_tokens: int, temperature: float, reasoning_effort: str) -> str:
    """Call LLM with automatic fallback: if one provider is rate-limited, try the other.
    
    Logic:
    1. Try primary provider (from LLM_PROVIDER env or passed explicitly)
    2. If rate-limited → try alternate provider
    3. If alternate also rate-limited → raise the original error
    
    This handles quota exhaustion gracefully: if Gemini is exhausted, fall back to Groq's
    3 keys × 3 models. If Groq is exhausted, fall back to Gemini (quota may have reset).
    """
    primary = (provider or default_provider()).lower()
    alternate = "groq" if primary == "gemini" else "gemini"
    
    # Try primary provider
    try:
        if primary == "gemini":
            return gemini_generate(messages, max_tokens=max_tokens, temperature=temperature)
        else:
            return groq_generate(messages, max_tokens=max_tokens, temperature=temperature,
                               reasoning_effort=reasoning_effort)
    except Exception as e:
        if not _is_rate_limit(e):
            raise  # Not a rate limit — propagate immediately
        
        # Primary provider rate-limited → try alternate
        print(f"[providers] {primary.upper()} rate-limited, falling back to {alternate.upper()}")
        try:
            if alternate == "gemini":
                return gemini_generate(messages, max_tokens=max_tokens, temperature=temperature)
            else:
                return groq_generate(messages, max_tokens=max_tokens, temperature=temperature,
                                   reasoning_effort=reasoning_effort)
        except Exception as e2:
            if _is_rate_limit(e2):
                # Both providers exhausted
                raise RuntimeError(
                    f"Both {primary.upper()} and {alternate.upper()} are rate-limited or unavailable. "
                    "Please try again in a few minutes."
                ) from e
            raise  # Alternate failed for non-rate-limit reason


def call_stream(messages: list[dict], provider: str | None, *,
                max_tokens: int, temperature: float,
                reasoning_effort: str) -> Iterator[str]:
    """Stream LLM response with automatic fallback if primary provider is rate-limited."""
    primary = (provider or default_provider()).lower()
    alternate = "groq" if primary == "gemini" else "gemini"
    
    try:
        if primary == "gemini":
            return gemini_stream(messages, max_tokens=max_tokens, temperature=temperature)
        else:
            return groq_stream(messages, max_tokens=max_tokens, temperature=temperature,
                             reasoning_effort=reasoning_effort)
    except Exception as e:
        if not _is_rate_limit(e):
            raise
        
        print(f"[providers] {primary.upper()} rate-limited (streaming), falling back to {alternate.upper()}")
        try:
            if alternate == "gemini":
                return gemini_stream(messages, max_tokens=max_tokens, temperature=temperature)
            else:
                return groq_stream(messages, max_tokens=max_tokens, temperature=temperature,
                                 reasoning_effort=reasoning_effort)
        except Exception as e2:
            if _is_rate_limit(e2):
                raise RuntimeError(
                    f"Both {primary.upper()} and {alternate.upper()} are rate-limited. "
                    "Please try again shortly."
                ) from e
            raise
