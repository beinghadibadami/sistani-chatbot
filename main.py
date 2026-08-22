"""FastAPI backend for the Sistani jurisprudence assistant.

Endpoints:
  GET  /health       liveness + index stats
  GET  /sources      available document sources (drives the UI scope filter)
  POST /chat         non-streaming answer
  POST /chat/stream  SSE: sources -> answer deltas -> followups -> done
  POST /feedback     anonymous rating, stored with the retrieved citations

Routes are async and blocking calls (Groq, HF embedding) run in worker threads, so one slow
generation does not block other users sharing a worker.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

load_dotenv()

from ingest.base import DOC_TITLES
from rag import feedback as feedback_store
from rag.generate import GROQ_MODEL, generate, stream_generate
from rag.providers import AVAILABLE_PROVIDERS, default_provider
from rag.retrieve import Hit, Retriever
from rag.rewrite import rewrite_query

DEFAULT_TOP_K = 5
MAX_TOP_K = 12

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the index once at startup rather than per request.
    print("Loading index...")
    retriever = Retriever()
    _state["retriever"] = retriever
    print(
        f"Index ready: {retriever.count} chunks | embed={retriever.backend} "
        f"| rerank={retriever.rerank_enabled} | provider={default_provider()} "
        f"| model={AVAILABLE_PROVIDERS.get(default_provider(), {}).get('model', GROQ_MODEL)} "
        f"| feedback={'on' if feedback_store.is_configured() else 'off'}"
    )
    yield
    _state.clear()


app = FastAPI(title="Sistani RAG API", version="2.0", lifespan=lifespan)


def _allowed_origins() -> list[str]:
    origins = {
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # A trailing slash is not a valid CORS origin and is ignored by browsers.
        "https://al-sistani-chat.onrender.com",
    }
    extra = os.getenv("FRONTEND_ORIGIN")
    if extra:
        origins.update(o.strip().rstrip("/") for o in extra.split(",") if o.strip())
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class PriorSource(BaseModel):
    """A passage retrieved on an earlier turn, replayed by the client.

    Length caps are security controls: these fields are inserted verbatim into a system
    prompt, so an unbounded prior_sources.text would be an injection vector.
    """

    citation: str = Field(..., max_length=300)
    text: str = Field(..., max_length=2000)
    doc_id: str | None = Field(default=None, max_length=64)
    chapter: str | None = Field(default=None, max_length=200)
    section: str | None = Field(default=None, max_length=200)
    locator: str | None = Field(default=None, max_length=100)


# Maximum total character budget for all history turns combined. A single turn at
# max_length=4000 × 6 turns = 24,000 chars of adversarial history is too much;
# this cap makes history a bounded surface while still allowing long conversations.
_HISTORY_MAX_CHARS = 12000
# A single turn can be large (e.g. a full answer), but cap it to prevent one turn
# dominating the budget and padding the prompt past the context limit.
_HISTORY_TURN_MAX_CHARS = 3000


def _sanitize_history(raw: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Strip dangerous role values and enforce character budgets on history content.

    Clients supply history and it is inserted directly into the prompt. Two vectors:
    1. A crafted "assistant" turn that appears to authorise malicious behaviour.
    2. A history turn with excessive length that expands the prompt beyond safe bounds.
    This function constrains both without blocking legitimate multi-turn conversations.
    """
    if not raw:
        return []
    cleaned: list[dict[str, str]] = []
    total = 0
    for turn in raw:
        role = (turn.get("role") or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        # Truncate individual turns rather than dropping them, so follow-up context
        # is never silently lost; the model sees a slightly truncated previous answer
        # rather than no context at all.
        content = content[:_HISTORY_TURN_MAX_CHARS]
        if total + len(content) > _HISTORY_MAX_CHARS:
            break
        cleaned.append({"role": role, "content": content})
        total += len(content)
    return cleaned


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    top_k: int = DEFAULT_TOP_K
    history: list[dict[str, str]] | None = None
    mode: str = Field(default="hybrid", pattern=r"^(hybrid|dense|bm25)$")
    doc_ids: list[str] | None = Field(default=None, max_length=7)
    prior_sources: list[PriorSource] | None = Field(default=None, max_length=8)
    provider: str | None = Field(default=None, pattern=r"^(groq|gemini)$")


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    question: str = Field(..., min_length=1, max_length=4000)
    answer: str | None = None
    rating: int = Field(..., ge=-1, le=1)
    comment: str | None = Field(default=None, max_length=2000)
    citations: list[dict[str, Any]] | None = None
    retrieval: dict[str, Any] | None = None


def get_retriever() -> Retriever:
    retriever = _state.get("retriever")
    if retriever is None:
        raise HTTPException(status_code=503, detail="Index is not loaded yet.")
    return retriever


def _clamp_k(k: int) -> int:
    return max(1, min(k, MAX_TOP_K))


def _scope(doc_ids: list[str] | None) -> set[str] | None:
    """Validate the requested scope against known documents."""
    if not doc_ids:
        return None
    valid = {d for d in doc_ids if d in DOC_TITLES}
    return valid or None


def _serialise(hit) -> dict:
    return {
        "citation": hit.citation,
        "doc_id": hit.doc_id,
        "chapter": hit.chapter,
        "section": hit.section,
        "locator": hit.locator,
        "score": round(hit.score, 4),
        "source": hit.source,
        "text": hit.text,      # enables expandable source cards in the UI
    }


def _prior_hits(payload: ChatRequest) -> list[Hit]:
    """Convert replayed client passages into Hits for the prompt builder."""
    return [
        Hit(
            score=0.0,
            text=p.text,
            citation=p.citation,
            doc_id=p.doc_id or "unknown",
            chapter=p.chapter,
            section=p.section,
            locator=p.locator,
        )
        for p in (payload.prior_sources or [])
    ]


def _retrieve(retriever: Retriever, payload: ChatRequest, sanitized_history=None):
    """Search for the current question.

    Uses sanitized_history for the rewrite call so the rewriter never sees raw
    client-supplied history content.
    """
    query, rewritten = rewrite_query(payload.question, sanitized_history or [])
    hits = retriever.search(
        query,
        _clamp_k(payload.top_k),
        mode=payload.mode,
        doc_ids=_scope(payload.doc_ids),
    )
    return hits, query, rewritten


@app.get("/health")
async def health():
    retriever = _state.get("retriever")
    return {
        "status": "ok" if retriever else "loading",
        "chunks": retriever.count if retriever else 0,
        "embed_backend": retriever.backend if retriever else None,
        "rerank": retriever.rerank_enabled if retriever else None,
        "provider": default_provider(),
        "model": AVAILABLE_PROVIDERS.get(default_provider(), {}).get("model", GROQ_MODEL),
        "feedback": feedback_store.is_configured(),
    }


@app.get("/sources")
async def sources():
    """Document sources with chunk counts, used to build the UI scope filter."""
    retriever = get_retriever()
    rows = retriever.conn.execute(
        "SELECT doc_id, COUNT(*) AS n FROM chunks GROUP BY doc_id ORDER BY n DESC"
    ).fetchall()
    return {
        "sources": [
            {"doc_id": r["doc_id"], "title": DOC_TITLES.get(r["doc_id"], r["doc_id"]), "chunks": r["n"]}
            for r in rows
        ]
    }


@app.get("/models")
async def list_models():
    """Available LLM providers and their models (used by dev UI model switcher)."""
    return {
        "providers": [
            {"id": k, **v}
            for k, v in AVAILABLE_PROVIDERS.items()
        ],
        "current": default_provider(),
    }


@app.post("/chat")
async def chat(payload: ChatRequest):
    retriever = get_retriever()
    # Provider override is only used in dev; in prod LLM_PROVIDER env var applies.
    provider = payload.provider if os.getenv("ALLOW_PROVIDER_OVERRIDE") else None
    try:
        sanitized_history = _sanitize_history(payload.history)
        hits, query, rewritten = await asyncio.to_thread(_retrieve, retriever, payload, sanitized_history)
        answer, followups = await asyncio.to_thread(
            generate, payload.question, hits, sanitized_history, _prior_hits(payload), provider
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "answer": answer,
        "sources": [_serialise(h) for h in hits],
        "followups": followups,
        "top_k": _clamp_k(payload.top_k),
        "retrieval_query": query if rewritten else None,
        "provider": provider or default_provider(),
    }


@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest):
    retriever = get_retriever()
    provider = payload.provider if os.getenv("ALLOW_PROVIDER_OVERRIDE") else None
    sanitized_history = _sanitize_history(payload.history)
    prior = _prior_hits(payload)

    async def event_stream():
        try:
            hits, query, rewritten = await asyncio.to_thread(_retrieve, retriever, payload)
            yield _sse(
                "sources",
                {
                    "sources": [_serialise(h) for h in hits],
                    "retrieval_query": query if rewritten else None,
                    "provider": provider or default_provider(),
                },
            )

            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def produce():
                try:
                    for kind, value in stream_generate(
                        payload.question, hits, sanitized_history, prior, provider
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, (kind, value))
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

            loop.run_in_executor(None, produce)

            while True:
                kind, value = await queue.get()
                if kind == "delta":
                    yield _sse("delta", {"text": value})
                elif kind == "followups":
                    yield _sse("followups", {"followups": value})
                elif kind == "error":
                    yield _sse("error", {"detail": value})
                else:
                    yield _sse("done", {})
                    break
        except Exception as exc:
            yield _sse("error", {"detail": str(exc)})
            yield _sse("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # stop proxies buffering away the streaming
        },
    )


@app.post("/feedback")
async def submit_feedback(payload: FeedbackRequest):
    if not feedback_store.is_configured():
        raise HTTPException(status_code=503, detail="Feedback storage is not configured.")

    ok, err = await asyncio.to_thread(
        feedback_store.submit,
        session_id=payload.session_id,
        question=payload.question,
        answer=payload.answer,
        rating=payload.rating,
        comment=payload.comment,
        citations=payload.citations,
        retrieval=payload.retrieval,
    )
    if not ok:
        raise HTTPException(status_code=502, detail=err or "Failed to store feedback.")
    return {"status": "ok"}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=int(os.getenv("WEB_CONCURRENCY", 1)),
    )
