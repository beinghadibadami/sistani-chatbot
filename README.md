# Sistani Jurisprudence Assistant

An AI-powered Islamic jurisprudence chatbot that answers questions based on the rulings of Ayatullah al-Sistani, with exact citations down to the ruling number, verse range, or Q&A reference.

Built for the Indian (Gujarati/Hindi-speaking) Shia community.

---

## What It Does

Ask a question about Islamic law, worship, or daily practice — get an answer grounded in a library of 7 authoritative texts, with the exact source cited so you can verify it yourself.

**Example:**
> **Q:** What is the kaffara for missing a fast?
>
> **A:** The kaffara for deliberately breaking a roza in Ramadan is one of: free a slave, fast for two consecutive months, or feed sixty poor people. For feeding, it's enough to give each person about 750g of dates, wheat, or similar food.
>
> *(Sistani Q&A — Fasting — Q1)*

---

## Features

### Retrieval & Answers
- **Hybrid search** — dense (FAISS/BGE embeddings) + lexical (BM25/FTS5) fused by Reciprocal Rank Fusion
- **Semantic chunking** — each document parsed by its own structure (rulings, verses, Q&A pairs, dialogue sections)
- **Contextual headers** — chapter/section metadata embedded with each chunk for better retrieval
- **Query rewriting** — follow-up questions like "what about for women?" get rewritten to standalone queries for correct retrieval
- **Exact citations** — every answer cites the specific ruling number, surah/verse range, or Q&A reference it drew from
- **Multi-turn conversations** — prior passages carried forward so follow-ups retain their subject
- **Document scoping** — filter search to specific texts (Quran only, Islamic Laws only, etc.)

### Indian Audience
- **Indian terminology** — uses namaz, roza, wazu, niyyat (not salat, sawm, wudu, niyyah)
- **Gujarati/Hindi support** — ask questions in Gujarati or Hindi and get answers in that language
- **Simple English** — answers written in everyday Indian English, not formal legal jargon
- **WhatsApp sharing** — share any ruling with your community via WhatsApp in one tap
- **Topic categories** — browse by Namaz, Roza, Taharat, Nikah, Hajj, Khums, Quran, Women's Rules

### UI/UX
- **Mobile-first responsive design** — works on 320px+ screens, all touch targets 44px+
- **Streaming answers** — text appears as it's generated, not after a long wait
- **Expandable source cards** — click a citation to read the actual retrieved passage
- **Bookmark rulings** — save important answers locally for quick reference later
- **Follow-up suggestions** — model suggests related questions after each answer
- **Cold-start awareness** — honest messaging when the free-tier service is waking up
- **Guest sessions** — chat persists locally without signup (localStorage)
- **Feedback** — thumbs up/down with optional comment, stored with retrieved citations for quality improvement
- **Islamic geometric design** — girih star tessellation, emerald/gold palette, serif typography for answers

### Technical
- **Dual LLM providers** — Groq (gpt-oss-120b, fastest) and Google Gemini (gemini-3.6-flash, free), switchable in dev mode
- **API key rotation** — multiple Groq keys with automatic failover on rate limits
- **Prompt security** — injection detection, XML-structured system prompt, output leak detection, input sanitization
- **Smart retrieval skipping** — greetings and small talk don't waste a retrieval call
- **Cross-encoder reranking** — implemented (off by default on free tier due to CPU cost)

---

## Source Library

| Document | Chunks | Citation granularity |
|---|---|---|
| Islamic Laws (4th Edition) | 2,950 | Individual ruling numbers (1–2796) |
| Holy Quran (English) | 745 | Surah + verse range |
| Sistani Q&A (scraped) | 701 | Topic + question number |
| Hajj Rituals | 482 | Rule numbers |
| Jurisprudence Made Easy | 277 | Dialogue section |
| Summary of the Rules of Worship | 194 | Issue numbers |
| Women's Religious Rules | 71 | Chapter + subsection |

**Total: 5,420 chunks** with 100% marker coverage on all numbered documents and all 114 Quran surahs verified.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Groq (gpt-oss-120b) / Google Gemini (gemini-3.6-flash) |
| Embeddings | BAAI/bge-small-en-v1.5 — local ONNX (build) / HuggingFace API (production) |
| Vector Store | FAISS IndexFlatIP (cosine similarity on unit vectors) |
| Lexical Search | SQLite FTS5 with BM25 scoring |
| Backend | Python, FastAPI, uvicorn |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Feedback | Supabase (insert-only RLS) |
| Deployment | Render (free tier) |

---

## Project Structure

```
ingest/          Build-time: PDF extraction, semantic chunking, embedding, index writing
  chunkers/      Per-document-type parsers (numbered, quran, qna, heading)
rag/             Run-time: retrieval, generation, rewriting, feedback, providers
  classify.py    Query classification (skip retrieval for greetings)
  retrieve.py    Hybrid search with RRF fusion + intent routing
  generate.py    Prompt construction, streaming, sentinel parsing
  providers.py   Groq + Gemini with key rotation
  rewrite.py     Follow-up query condensation
  feedback.py    Supabase anonymous feedback
frontend/        Next.js chat interface
  components/    UI components (message-bubble, source-cards, empty-state, etc.)
  lib/           API client, session management, bookmarks, types
artifacts/       Pre-built index (index.faiss + chunks.sqlite) — deployed directly
tools/           Verification, benchmarks, diagnostics (20 scripts)
scripts/         Data acquisition (Q&A scraper)
main.py          FastAPI backend with SSE streaming
ARCHITECTURE.md  Full technical reference documentation
```

---

## License

This project uses publicly available Islamic texts for educational purposes. The rulings and source materials are the intellectual property of the Office of Ayatullah al-Sistani. This tool is not affiliated with or endorsed by the Office.
