# Sistani Jurisprudence Assistant — Architecture Reference

A RAG chatbot answering Islamic jurisprudence questions from a fixed library of texts, with
citations resolved down to the exact ruling, issue, or verse range.

This document is the reference for picking the project back up after time away. It records not
just what the system does but **why** each decision was made, including the constraints that
forced them and the measurements that justified them.

---

## 1. Quick orientation

```
ingest/     BUILD TIME  — parse PDFs, chunk semantically, embed, write index
rag/        RUN TIME    — retrieve, generate, feedback
tools/      DEV         — verification, benchmarks, diagnostics
scripts/    DATA        — source acquisition (Q&A scraper)
artifacts/  OUTPUT      — index.faiss + chunks.sqlite (deployed; checkpoint/ is gitignored)
frontend/   UI          — Next.js chat interface
main.py     API         — FastAPI: /chat, /chat/stream, /sources, /feedback, /health
```

### Everyday commands

```bash
# Rebuild the index (resumes from checkpoint; only re-embeds what changed)
python -m ingest.build_index

# Chunk counts and token totals, no embedding
python -m ingest.run_all

# Verify the built index (vector/metadata agreement, unit norms, citations)
python tools/verify_index.py

# Try retrieval from the CLI
python tools/search.py "Is abortion permissible?" --compare

# Run the API
python main.py
```

---

## 2. Data pipeline (build time)

### 2.1 Source documents

Seven works, ~22 MB of PDF plus one scraped text file, in `data/`:

| doc_id | Source | Atomic unit | Token cap |
|---|---|---|---|
| `islamic_laws` | Islamic Laws, 4th ed. | `Ruling N.` | 470 |
| `summary_worship` | Summary of the Rules of Worship | `Issue N:` | 470 |
| `hajj_rituals` | Hajj Rituals | `Rule N:` | 470 |
| `quran` | Holy Quran (English) | verse ranges | 300 |
| `sistani_qna` | Scraped sistani.org Q&A | Q&A pair | 470 |
| `women_rules` | Women's Religious Rules | TOC subsection | 400 |
| `jurisprudence_easy` | Jurisprudence Made Easy | dialogue section | 400 |

Nahjul Balagha and `book-46.pdf` are present but **not ingested** (deferred).

**Why per-document caps:** a self-contained legal ruling tolerates a larger chunk than a dense
scripture passage. Caps are also constrained by the embedding model — see §3.2.

### 2.2 Extraction — `ingest/extract.py`

Uses **PyMuPDF** (`fitz`), not PyPDF2, because it exposes font size and weight per text span.
That metadata is what makes heading detection possible in documents with no numeric markers.

Two non-obvious fixes live here:

- **De-hyphenation.** The Quran PDF breaks words across lines (`Mer-` / `ciful`,
  `hospital-` / `ity`). Left alone this corrupts both the stored text and its embedding.
  Repair is applied to *raw* text before punctuation normalisation, because normalisation maps
  en/em dashes onto `-` and would otherwise trigger false joins.
- **`is_plausible_heading()`.** Islamic Laws renders inline Arabic (Quranic phrases, marriage
  contract formulas) at ~16.1 pt — exactly the chapter-title size. Pure size matching captured
  those as chapter titles, giving ~700 chunks citations like
  `Islamic Laws — زَوّجْتُكَ إِحْدَىٰ بَنَاتِي … — Ruling 2471`. Headings containing Arabic
  script, or longer than 130 chars, are rejected.

### 2.3 Chunking — `ingest/chunkers/`

Every document reduces to: *find the smallest reliable atomic marker, track headings above it
for context, split further only on token overflow.* Three chunker families cover all seven:

**`numbered.py`** — `islamic_laws`, `summary_worship`, `hajj_rituals`.
Regex on the numeric marker, with chapter/section tracked by font size. **The marker is checked
before font size** because these PDFs occasionally typeset a ruling in heading size — Islamic
Laws `Ruling 989.` is set at 16.1 pt and was silently swallowed as a chapter title until this
ordering was fixed.

**`quran.py`** — surah/verse grouping. Three PDF-specific facts:
- The per-page running header names the surah that *starts* on that page, so it is **not** a
  reliable "current surah" signal (a page ending surah 54 and starting 55 is headed 55). It is
  skipped by vertical position; the 10.6 pt body title is the authoritative boundary.
- Verse-opening lines carry a `Garamond-Bold` span; continuation lines do not. Detecting verses
  by font is more robust than regex, since a wrapped line can also begin with a digit.
- A single verse is too small to retrieve alone, so consecutive verses are grouped to the cap,
  never across a surah boundary, recording an exact `verse_start`/`verse_end`.

**`heading.py`** — `women_rules`, `jurisprudence_easy`. Font-based heading detection, then
recursive packing at dialogue-turn boundaries. `jurisprudence_easy` has no finer marker than its
`Dialogue on X` sections, so its citations are necessarily coarser — a source limitation, not a
parser one.

**`qna.py`** — `sistani_qna`. Already structured as `===== Topic =====` blocks with `Qn:`/`An:`
pairs. A question is kept with its answer because neither retrieves usefully alone.

### 2.4 Contextual headers — the key retrieval decision

Each chunk stores **two** text fields:

| Column | Contents | Used for |
|---|---|---|
| `text` | clean body | sent to the LLM, shown in the UI |
| `embed_text` | `citation header \n body` | **the vector**, and the BM25 index |

**Why.** Vectors built from the body alone carry no structural provenance. `Ruling 2747` reads
in full: *"A husband and wife inherit from one another as per the details that will be mentioned
later."* The words "inheritance" and "Irth" never appear, and many rulings are bare
cross-references that are nearly meaningless in isolation. Prepending
`Islamic Laws (4th Edition) | Inheritance (Irth) | Ruling 2747` fixes that, and simultaneously
makes chapter names lexically searchable via BM25 (searching "Irth" or "al-Jumu'ah" previously
hit almost nothing).

**Header budget: 32 tokens** (`HEADER_TOKEN_BUDGET`), degrading by dropping the least specific
parts first so the locator always survives. This is not cosmetic: BGE truncates at 512 tokens,
and unbudgeted full citations pushed 60 chunks over the limit (worst case 557), silently
dropping their tails. Budgeting plus reduced caps brings overflow to **0**, and saved 43 K
tokens of embedding work as a side effect.

**Known trade-off:** every chunk in a chapter now shares an identical header, which makes them
slightly more similar to one another. Discrimination *across* chapters improves; *within* a
chapter it marginally worsens. Net positive, but not free.

### 2.5 Embedding — `ingest/embed.py`

Model: **`BAAI/bge-small-en-v1.5`** (384-dim, 67 MB ONNX). Two interchangeable backends,
verified to produce the same vectors (**cosine 0.999999** on identical text):

- **`local`** — `fastembed` + ONNX Runtime, no PyTorch. Used to build the index: no rate
  limits, no per-call network cost.
- **`api`** — HuggingFace Inference API. Used in production; see §5.

Two things that are easy to get wrong:

1. **BGE retrieval is asymmetric.** Queries need the instruction prefix
   `"Represent this sentence for searching relevant passages: "`; passages must not have it.
   `fastembed`'s `query_embed()` **does not apply it** (it is byte-identical to `embed()`), so
   it is applied explicitly. Omitting it silently degrades retrieval.
2. **Output is already L2-normalised** (norm = 1.000000), so a FAISS inner-product index is
   exact cosine similarity with no further work.

**Build cost:** ~917 K tokens, ~80 min on 4 CPU cores (~190 tok/s). Measured: explicit thread
tuning makes it *worse* (default 193 tok/s vs 149 at `threads=4` vs 123 at `threads=8`) —
oversubscription on 4 cores. Progress is checkpointed per 256-chunk block, written to a temp
file then renamed so an interrupt cannot leave a partial block. A **fingerprint** over
`MODEL_NAME + chunk count + sampled embed_text` invalidates the checkpoint whenever chunking or
header construction changes, which prevents silently mixing stale vectors into a new build.

### 2.6 Storage — `ingest/store.py`

- **`artifacts/index.faiss`** — `IndexFlatIP` over unit vectors. Deliberately *not* `IndexFlatL2`:
  the previous pipeline used L2, which ranks by Euclidean distance and is not what BGE is
  trained for.
- **`artifacts/chunks.sqlite`** — metadata + FTS5. Replaces a pickle so citations are queryable
  and rows can be added without rewriting a blob.
- **`chunks_fts`** — FTS5 virtual table over `embed_text`, `tokenize='porter unicode61'`,
  `content='chunks'` (external content, so text is not stored twice).

**Why FTS5 for BM25:** it ships with Python's `sqlite3`, so it adds no dependency, and the index
lives on disk rather than as tokenised documents in RAM — which matters on a 512 MB host. It
measured **14 ms** per query.

A flat FAISS file is the right choice at this scale (5,420 vectors ≈ 8 MB). A hosted vector DB
would add a network hop and a bill to solve problems this project does not have.

---

## 3. Retrieval (run time) — `rag/retrieve.py`

### 3.1 The pipeline

```
question
   │
   ├─ DENSE      embed query (BGE + prefix) → FAISS IndexFlatIP → top 150
   │
   └─ LEXICAL    expand synonyms → FTS5 MATCH → BM25 → top 150
                            │
                    RRF fusion  (rank-based, not score-based)
                            │
                 [+ intent-scoped reserved slots]
                            │
                     top k (default 5)
                            │
                 [optional cross-encoder rerank — OFF]
```

### 3.2 Reciprocal Rank Fusion

`score(d) = Σ_lists 1 / (60 + rank_d)`

**Why RRF rather than averaging scores:** cosine similarity and BM25 are on incomparable
scales, and RRF consumes only the *rank* from each list, so no normalisation is needed.

### 3.3 Query expansion — `rag/expand.py`

A static synonym map (`friday ↔ jumuah ↔ congregation`, `ablution ↔ wudu`,
`inheritance ↔ irth`, …) applied **only to the BM25 query**. The dense query is left untouched
because the embedding model handles paraphrase itself, and padding it with synonyms blurs it.

These documents mix English with transliterated Arabic, and BM25 matches literal tokens, so
without expansion "ablution" never reaches a ruling that says "wuduh".

### 3.4 Document-intent routing

Fiqh manuals dominate the corpus by volume, so *"which **verses** describe the Friday
congregational prayer?"* returned manuals and not Quran 62:9-11.

Diagnosis (`tools/diagnose_recall.py`) showed this was a **recall** problem, not a ranking one:
the target chunk was **not in the dense top 300**, and sat at BM25 rank 175. Reranking cannot
fix that — a reranker only reorders what stage 1 returned.

A score multiplier could not fix it either: at rank 118 a chunk scores ~0.0056 in RRF against
~0.032 at the top, needing an arbitrary ~6× boost that would distort every other query.

**The fix:** when a question explicitly names a source type (`verse`, `surah`, `ayah`, …), run
an additional retrieval **scoped to those doc_ids** and reserve ~40 % of `k` for the results.
Deterministic, and it only affects questions that actually name a source type. Surah 62 now
surfaces, tagged `intent` in the UI.

### 3.5 Explicit scoping (UI filter)

`Retriever.search(doc_ids={...})` restricts retrieval: a SQL join for BM25, and a post-filter
for dense (FAISS `IndexFlatIP` cannot filter natively, so scoped dense search retrieves ~6× deeper
and then drops non-matching docs — cheap at this corpus size).

**Explicit user scoping is preferred over inferring intent**: unambiguous, zero latency, and it
is actual rather than guessed intent. When a scope is supplied, the §3.4 heuristic is skipped.

### 3.6 Cross-encoder reranking — implemented, OFF by default

A **bi-encoder** (what powers retrieval) embeds query and document *separately*, so all 5,420
document vectors are precomputed once and a query is a single dot product. Fast, but the model
never sees query and document together.

A **cross-encoder** takes `[CLS] query [SEP] document [SEP]` as one input, so full attention runs
across both. Much more accurate, but nothing can be precomputed — one forward pass per
(query, document) pair. Fine for 30 candidates, impossible for 5,420. Hence stage 2 only.

**Why it is off** (measured, `tools/bench_rerank.py`, 4 cores):

| Docs | Time |
|---|---|
| 5 | 0.77 s |
| 10 | 1.61 s |
| 30 | 6.90 s |

On Render free tier (~0.1 shared CPU) that is minutes. Enable with `RERANK=1` only on real
hardware.

---

## 4. Generation — `rag/generate.py`

Model: **`openai/gpt-oss-120b`** on Groq (131 K context, ~500 tok/s, $0.15/$0.60 per 1M
in/out). The previous `meta-llama/llama-4-scout-17b-16e-instruct` has been **removed from
Groq's model list**, so this migration was mandatory, not optional.

`reasoning_effort="low"` — fiqh Q&A over retrieved context does not need deep chain-of-thought,
and it keeps time-to-first-token down. Groq rejects `"none"`; `low` is the floor.

### 4.1 Multi-turn / follow-up handling

**The problem.** Retrieval never sees chat history — `Retriever.search()` takes a string, embeds
it, and searches FAISS. So:

```
Turn 1: "Is abortion permissible?"          → good retrieval
Turn 2: "what about for women with health risks?"
        → embedded literally; matches "women" and "health", loses "abortion"
```

Putting history in the prompt does **not** fix this, because that happens *after* retrieval.

Two mechanisms address this. Both are active, and they operate on different layers.

#### (a) Query rewriting — `rag/rewrite.py` — ON by default

Condenses history + question into one standalone retrieval query using `gpt-oss-20b` at
`reasoning_effort="low"`. Only the *retrieval* query is rewritten; the answer model still
receives the user's original wording, so phrasing and tone survive.

Measured against the real index (`tools/test_followup.py`), after asking
*"Is abortion permissible in Islam?"*:

| Follow-up | Without rewriting | With rewriting |
|---|---|---|
| "what is the kaffara for it?" | kaffara for **ihram / fasting** | **Abortion Q5** ✓ |
| "what about for women with health risks?" | Contraceptives Q5, menstrual cycles | **Abortion Q7, Q2** ✓ |
| "is it allowed after four months?" | **Marriage** Rulings 2436, 2440 | **Abortion Q6, Q4, Q2** ✓ |

The third case is the clearest argument for it: "four months" also appears in marriage
waiting-period contexts, so the raw follow-up retrieves marriage law and the model would answer
a ruling question from entirely the wrong chapter.

Cost: **~400 ms warm**, and only when a conversation has history — first questions pay nothing.

#### (b) Carry prior passages forward — zero added latency

The client replays the previous turn's retrieved passages as `prior_sources`. The backend merges
them into a separate, clearly-labelled prompt block, deduplicated against this turn's results and
capped at a smaller budget (8 K vs 24 K chars) so they can never crowd out passages retrieved for
the actual question. Cost: ~750 prompt tokens (~$0.0001), no extra call.

#### Why both, and which does the real work

Rewriting is the stronger fix, and this is measurable: in all three cases above it surfaced
**2-3 passages that turn 1 never retrieved**, so replaying prior chunks could not have covered
them. Carry-forward can only ever resurface what a previous turn happened to find; rewriting goes
and locates the correct passage. It fixes the root cause.

Carry-forward is retained because it is free and covers the opposite case — where the previous
turn's passages remain the best evidence and this turn's retrieval drifts.

History in the prompt is a third, separate concern: it is what lets the model resolve "it" in
*"what is the kaffara for it?"*, since it receives the original wording rather than the rewrite.

Set `REWRITE_QUERY=0` to disable (a) and rely on (b) alone.

### 4.2 Follow-up suggestions

Generated in the **same completion** as the answer, after a `<<<FOLLOWUPS>>>` sentinel — ~40
output tokens instead of a second round trip. The streaming parser withholds any tail that could
still become the sentinel, so the marker never appears in the visible answer. Absence of the
sentinel is handled gracefully.

### 4.3 Shared Groq client — `rag/groq_client.py`

Constructing a client per request costs a TLS handshake on **every** call. Measured: rewrite
latency dropped **1390 ms → ~360 ms** once the connection was reused. Applies to answers too.

---

## 5. Deployment (Render free tier)

Free tier means **512 MB RAM, ~0.1 shared CPU, sleeps after 15 min idle** (30-60 s cold start).

**This drives the central architectural split:**

| | Where | Why |
|---|---|---|
| Document embedding | local, `fastembed` | one-time, no rate limits |
| Query embedding | **HF API** (`EMBED_BACKEND=api`) | keeps ONNX out of RAM |

Running ONNX in production would need ~150-250 MB RSS on a 512 MB cap, and a query measured at
119 ms on 4 dedicated cores would take **seconds** on 0.1 CPU. Using the API drops the footprint
to roughly 100 MB. This is only possible because the two backends produce interchangeable
vectors (§2.5).

### Latency (measured end-to-end via `tools/test_api.py`)

| | First request (cold process) | Subsequent (warm) |
|---|---|---|
| Time to first token | ~9.3 s | **~4.4 s** |
| Complete answer | ~10.0 s | ~5.0 s |

Approximate warm breakdown:

| Stage | Warm |
|---|---|
| Query rewrite (`gpt-oss-20b`, only with history) | ~400 ms |
| Query embed (HF API) | ~300 ms |
| BM25 (FTS5) | 14 ms |
| FAISS | < 5 ms |
| Groq TTFT with a full context prompt | ~3.5 s |

**Note on the Groq figure.** An isolated `gpt-oss-120b` call with a two-message prompt returns
its first token in ~1.5 s, and an early estimate of ~2 s end-to-end was built on that number.
That was wrong: real prompts carry 5 retrieved passages (~3-4 K tokens) plus prior-turn
passages, and the model reasons before emitting, so TTFT scales up substantially. Treat ~4.4 s
warm as the realistic figure.

Cold start on the free tier adds 30-60 s on top when the service has slept, which is why
`ThinkingIndicator` escalates its wording instead of showing a silent spinner.

### Environment variables

| Var | Purpose |
|---|---|
| `GROQ_API_KEY` | answers + optional rewriting |
| `HF_TOKEN` | query embedding via API |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | feedback storage |
| `EMBED_BACKEND` | `api` (default) or `local` |
| `RERANK` | `0` (default) — see §3.6 |
| `EXPAND` | `1` (default) — synonym expansion + intent routing |
| `REWRITE_QUERY` | `1` (default) — follow-up query condensing, see §4.1 |
| `GROQ_REWRITE_MODEL` | `openai/gpt-oss-20b` |
| `FRONTEND_ORIGIN` | extra CORS origins (comma-separated) |
| `WEB_CONCURRENCY` | uvicorn workers |
| `NEXT_PUBLIC_BACKEND_URL` | frontend → backend |

---

## 6. API

| Endpoint | Purpose |
|---|---|
| `GET /health` | status, chunk count, backend, model |
| `GET /sources` | doc list + chunk counts (drives the UI scope filter) |
| `POST /chat` | non-streaming answer |
| `POST /chat/stream` | SSE: `sources` → `delta`* → `followups` → `done` |
| `POST /feedback` | anonymous rating |

Routes are `async`; blocking Groq/HF calls run via `asyncio.to_thread` so one slow generation
does not block other users on the same worker. Streaming bridges the blocking Groq iterator into
the event loop through a queue.

Sources are emitted **before** the answer so citations render while text is still generating.

---

## 7. Frontend — `frontend/`

Next.js 16 / React 19 / Tailwind v4.

**Design intent:** Islamic manuscript illumination — emerald ink, antique gold, warm paper
rather than clinical white; neutrals carry a deliberate warm/green cast because pure greys are
what make an interface read as generic. Answers are set in a **serif** (Spectral) against an
unbubbled gold margin rule, so they read as scholarly prose rather than chat output. The
backdrop is a static SVG **girih star tessellation**, replacing a WebGL aurora that was both
generic and a continuously-running fragment shader.

| File | Role |
|---|---|
| `lib/session.ts` | guest UUID + `localStorage` chat/scope persistence |
| `lib/api.ts` | SSE client, sources, feedback |
| `components/source-cards.tsx` | expandable citations — click to read the retrieved passage |
| `components/scope-filter.tsx` | restrict retrieval to chosen sources |
| `components/thinking-indicator.tsx` | escalating copy for free-tier cold starts |
| `components/feedback-buttons.tsx` | rating; negative opens a comment box |
| `components/geometric-backdrop.tsx` | girih tessellation |

**Guest sessions:** a `crypto.randomUUID()` in `localStorage`. No signup, no server-side chat
storage. Conversations persist on the device only; the UUID travels with feedback so multiple
submissions can be correlated without identifying anyone.

---

## 8. Feedback — `rag/feedback.py`

Supabase REST, written **from the backend** so the key is never shipped to browsers.

Storing the retrieved `citations` alongside the rating is the entire point: "this answer was
wrong" is not actionable, but "this answer was wrong **and these are the chunks that were
retrieved**" is. Passage bodies are stripped client-side — the citation identifies the chunk.

Failures are swallowed: feedback is telemetry and must never surface as a chat error.

RLS is **insert-only for `anon`**, with deliberately no select policy — an anon key that could
read the table back would expose every question users have asked.

Table DDL: `python tools/setup_supabase.py` (add `--test` to verify connectivity).

---

## 9. Verification

Correctness here is checked against ground truth, not just "it ran":

| Tool | Checks |
|---|---|
| `tools/verify_coverage.py` | every `Ruling`/`Issue`/`Rule` marker in the raw PDF appears in the chunks |
| `tools/verify_quran.py` | all 114 surahs against canonical verse counts |
| `tools/verify_index.py` | vector/metadata agreement, unit norms, IP metric, citations |
| `tools/audit_citations.py` | chapter/section titles containing Arabic or implausibly long |
| `tools/measure_headers.py` | header token cost and 512-token overflow |
| `tools/inspect_chunks.py` | per-doc stats + sample chunks |
| `tools/diagnose_recall.py` | why a known-relevant chunk did not surface |
| `tools/search.py` | CLI retrieval, `--compare` across dense/bm25/hybrid |
| `tools/bench_rerank.py`, `tools/bench_rewrite.py` | latency of optional stages |

**Current state:** 2,796/2,796 Ruling markers, 165/165 Issue, 430/430 Rule, 114/114 surahs with
complete verse coverage, 0 chunks over cap, 0 header overflow.

Note: `hajj_rituals` genuinely skips 24 rule numbers (161, 305, 314-321, …) — verified absent
from the source text, not a parsing loss.

---

## 10. Deferred / known gaps

- **Nahjul Balagha and `book-46.pdf`** are not ingested.
- **`jurisprudence_easy` and `women_rules` have no locators** (0 % coverage) — those sources
  contain no numbered units, so citations stay heading-level.
- **Legacy files still present:** `sistani_rag.py`, `sistani_faiss_with_qna.index`,
  `sistani_new_chunks.pkl`, `streamlit_app.py`. Removable once the new stack is confirmed
  end-to-end; `streamlit_app.py` still imports the old module.
- **No automated test suite** — verification is via the `tools/` scripts above.
- **`next.config.mjs` sets `typescript.ignoreBuildErrors: true`**, so type errors do not fail
  the build. Run `npx tsc --noEmit` manually.
