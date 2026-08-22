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

def _groq_kwargs(messages: list[dict], stream: bool, max_tokens: int,
                 temperature: float, reasoning_effort: str) -> dict:
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    kw = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "top_p": 1,
        "stream": stream,
    }
    if "gpt-oss" in model and reasoning_effort:
        kw["reasoning_effort"] = reasoning_effort
    return kw


def groq_generate(messages: list[dict], *, max_tokens: int, temperature: float,
                  reasoning_effort: str) -> str:
    from rag.groq_client import get_client
    kw = _groq_kwargs(messages, stream=False, max_tokens=max_tokens,
                      temperature=temperature, reasoning_effort=reasoning_effort)
    c = get_client().chat.completions.create(**kw)
    return c.choices[0].message.content or ""


def groq_stream(messages: list[dict], *, max_tokens: int, temperature: float,
                reasoning_effort: str) -> Iterator[str]:
    from rag.groq_client import get_client
    kw = _groq_kwargs(messages, stream=True, max_tokens=max_tokens,
                      temperature=temperature, reasoning_effort=reasoning_effort)
    for chunk in get_client().chat.completions.create(**kw):
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

def _gemini_client():
    from google import genai
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=key)


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
    client = _gemini_client()
    model = _gemini_model()
    system_instruction, contents = _to_gemini_contents(messages)

    cfg = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
    )
    resp = client.models.generate_content(model=model, contents=contents, config=cfg)
    return resp.text or ""


def gemini_stream(messages: list[dict], *, max_tokens: int, temperature: float,
                  **_: Any) -> Iterator[str]:
    from google.genai import types
    client = _gemini_client()
    model = _gemini_model()
    system_instruction, contents = _to_gemini_contents(messages)

    cfg = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
    )
    for chunk in client.models.generate_content_stream(
        model=model, contents=contents, config=cfg
    ):
        if chunk.text:
            yield chunk.text


# ---------------------------------------------------------------------------
# Unified dispatch
# ---------------------------------------------------------------------------

def call_generate(messages: list[dict], provider: str | None, *,
                  max_tokens: int, temperature: float, reasoning_effort: str) -> str:
    p = (provider or default_provider()).lower()
    if p == "gemini":
        return gemini_generate(messages, max_tokens=max_tokens,
                               temperature=temperature)
    return groq_generate(messages, max_tokens=max_tokens, temperature=temperature,
                         reasoning_effort=reasoning_effort)


def call_stream(messages: list[dict], provider: str | None, *,
                max_tokens: int, temperature: float,
                reasoning_effort: str) -> Iterator[str]:
    p = (provider or default_provider()).lower()
    if p == "gemini":
        return gemini_stream(messages, max_tokens=max_tokens, temperature=temperature)
    return groq_stream(messages, max_tokens=max_tokens, temperature=temperature,
                       reasoning_effort=reasoning_effort)
