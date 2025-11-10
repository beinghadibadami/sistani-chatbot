# main.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sistani_rag import load_index, search_similar, generate_answer, TOP_K

# ---------- FastAPI Init ----------
app = FastAPI(title="Sistani RAG API", version="1.0")

# Allow frontend calls (Next.js, React, etc.)
# Configure CORS to allow specific frontend origin plus localhost as fallback
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")
allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if FRONTEND_ORIGIN and FRONTEND_ORIGIN not in allowed_origins:
    allowed_origins.insert(0, FRONTEND_ORIGIN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Load Index Once at Startup ----------
print("🔥 Loading FAISS index + chunks...")
index, chunks, sources = load_index()
print("✅ Loaded successfully")


# ---------- Request Model ----------
class Query(BaseModel):
    question: str
    top_k: int = TOP_K


# ---------- Routes ----------
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "API is running!"}


@app.post("/chat")
def chat_with_rag(payload: Query):
    try:
        question = payload.question
        top_k = payload.top_k

        # Search similar chunks
        top_chunks = search_similar(
            question, index, chunks, sources, k=top_k
        )

        # LLM answer
        answer = generate_answer(top_chunks, question)

        # Extract sources only
        used_sources = [src for _, src in top_chunks]

        return {
            "answer": answer,
            "sources": used_sources,
            "top_k": top_k,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Run Local ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
