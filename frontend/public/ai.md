# Sistani Jurisprudence Assistant - AI Agent Documentation

## Overview

**Name:** Sistani Jurisprudence Assistant  
**URL:** https://al-sistani-chat.onrender.com  
**Type:** Islamic Jurisprudence Q&A System  
**Provider:** Al-Sistani Chat  
**Version:** 1.0

## Purpose

This AI assistant provides authentic Islamic rulings (fatwa) from Grand Ayatollah Sayyid Ali al-Husayni al-Sistani's official sources. It answers questions about Shia Ja'fari fiqh (Islamic jurisprudence) with citations to authoritative texts.

## Capabilities

### Question Answering
- **Prayer (Salat)**: conditions, times, qada, congregational prayer
- **Fasting (Sawm)**: Ramadan rules, things that break fast, fidya
- **Hajj & Umrah**: rituals, prohibitions, obligations
- **Purity (Tahara)**: wudu, ghusl, najis substances, purification
- **Marriage & Divorce**: nikah, mut'ah, talaq, iddah
- **Dietary Laws**: halal/haram foods, slaughter requirements
- **Financial**: zakat, khums, ribā, business transactions
- **Inheritance**: distribution, wills, bequests
- **Daily Practice**: social conduct, clothing, music, entertainment

### Multilingual Support
- **English** (primary)
- **Hindi/Urdu** (Devanagari and Roman script)
- **Gujarati** (Gujarati script and Roman transliteration)
- **Arabic** (queries and citations)

### Technical Features
- Real-time streaming responses
- Source citation with every answer
- Retrieval-augmented generation (RAG) over 2000+ document chunks
- BM25 + FAISS hybrid search
- Context-aware follow-up handling
- Automatic query translation for non-English inputs

## Knowledge Base

### Primary Sources
1. **Sistani Q&A Database** - Official question-answer collection from sistani.org
2. **Islamic Laws (4th Edition)** - Comprehensive Shia fiqh manual
3. **Jurisprudence Made Easy** - Dialogue-format practical rulings
4. **Hajj Rituals** - Complete pilgrimage guide
5. **Summary of Rules of Worship** - Daily practice essentials
6. **Women's Religious Rules** - Gender-specific rulings
7. **Nahjul Balagha** - Selected jurisprudential excerpts
8. **Holy Quran** - English translation (references)

### Authority
All rulings follow the fatwa of Grand Ayatollah Sayyid Ali al-Husayni al-Sistani, one of the most widely followed Shia marja' (source of emulation) globally.

## Usage Guidelines

### For End Users
1. Ask questions in natural language (any supported language)
2. Questions can be specific ("What breaks wudu?") or general ("Tell me about prayer")
3. Review cited sources for verification
4. Use follow-up questions for clarification
5. Bookmark important rulings for later reference

### For AI Agents
- **Query the API**: POST to `/api/chat` with JSON `{"question": "your question"}`
- **Streaming**: Use Server-Sent Events for real-time token streaming
- **Context**: The system maintains conversation history automatically
- **Citations**: Every answer includes source references in the response metadata

### Example Queries
```
"Is listening to music haram?"
"What are the conditions for wudu?"
"namaz ke liye wazu kaise karein" (Hindi)
"mane kem khbr pade hu baaligh chu k nahi" (Gujarati)
"Can I pray with shoes on?"
"What makes a marriage valid?"
```

## API Endpoints

### Chat Endpoint
```
POST /api/chat
Content-Type: application/json

{
  "question": "string",
  "history": [
    {"role": "user", "content": "string"},
    {"role": "assistant", "content": "string"}
  ],
  "provider": "gemini|groq",
  "mode": "hybrid|bm25|faiss"
}
```

Response: Server-Sent Events stream with:
- `data: {"delta": "text chunk"}`
- `data: {"sources": [...]}`
- `data: {"done": true}`

### Health Check
```
GET /health

Response: {"status": "ok", "chunks": 2000, "embed_backend": "gemini"}
```

## Limitations

- **Scope**: Only Islamic jurisprudence per Ayatollah Sistani's rulings
- **Not fatwa issuance**: Answers are informational; consult a scholar for personal rulings
- **Source-bound**: Cannot answer questions outside the indexed corpus
- **No medical/legal advice**: Consult professionals for health or legal matters
- **Madhab-specific**: Follows Shia Ja'fari fiqh exclusively

## Trust & Safety

- All answers cite authoritative sources
- System declines off-topic questions
- No generation of harmful or inappropriate content
- Transparent about scope and limitations
- Encourages consultation with qualified scholars for critical matters

## Technical Stack

- **Frontend**: Next.js 15, React, TailwindCSS
- **Backend**: FastAPI, Python 3.11+
- **Search**: FAISS (vector), BM25 (keyword), hybrid ranking
- **LLM**: Google Gemini (primary), Groq (fallback)
- **Embeddings**: text-embedding-004
- **Deployment**: Render

## Contact

- **Web**: https://al-sistani-chat.onrender.com
- **Source**: Grand Ayatollah Sayyid Ali al-Husayni al-Sistani
- **Corpus**: sistani.org official publications

---

*This assistant is for educational purposes. For personal fatwa, consult a qualified scholar or the office of your marja'.*
