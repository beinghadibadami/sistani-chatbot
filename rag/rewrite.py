"""Rewrite follow-up questions into standalone retrieval queries.

Retrieval never sees the chat history: `Retriever.search()` embeds the question string and
searches FAISS. So a follow-up like "what about for women with health risks?" is embedded
literally, retrieves passages about women and health, and the model then answers confidently
from the wrong sources. Putting history in the *generation* prompt does not fix this, because
that happens after retrieval.

This step therefore condenses history + question into one self-contained question, and only
that rewritten form is used for retrieval. The original question is still what the answer
model sees, so phrasing and tone are preserved.

Rather than heuristically detecting "is this a follow-up?" (brittle, and wrong on the cases
that matter), the model is always asked and instructed to echo self-contained questions
verbatim. A small fast model is used because this is a trivial transformation.
"""

from __future__ import annotations

import os
from typing import Sequence

# On by default: measured against the real index, it is the only mechanism that recovers a
# follow-up whose answer lies outside the previous turn's retrieval. Asking "what is the kaffara
# for it?" after an abortion question retrieves kaffara rulings for ihram and fasting, while the
# rewritten "What is the kaffara for abortion?" returns the correct Q&A as the top hit - and the
# needed passage was absent from the previous turn, so replaying prior chunks could not help.
# Costs ~360ms warm, and only fires once a conversation has history.
REWRITE_ENABLED = os.getenv("REWRITE_QUERY", "1") == "1"
REWRITE_MODEL = os.getenv("GROQ_REWRITE_MODEL", "openai/gpt-oss-20b")
REWRITE_REASONING_EFFORT = os.getenv("GROQ_REWRITE_REASONING_EFFORT", "low")
REWRITE_MAX_TOKENS = 120
HISTORY_TURNS = 6

# Long inputs are almost always already self-contained, and rewriting them risks losing
# detail; this also caps the cost of the extra call.
MAX_REWRITE_CHARS = 400

SYSTEM = """You rewrite a user's latest question into a single self-contained search query.

Rules:
- If the latest question is already self-contained, output it EXACTLY as given, unchanged.
- If it depends on the conversation (pronouns like "it"/"that", or elliptical forms like \
"what about...", "and if...", "for women?"), rewrite it into one standalone question that \
names the subject explicitly.
- Preserve the user's language. Do not translate.
- Preserve all qualifiers (who, when, conditions) from the conversation that the question \
relies on.
- Output ONLY the rewritten question. No preamble, no quotes, no explanation.
"""

FEWSHOT = [
    {
        "role": "user",
        "content": (
            "Conversation:\n"
            "user: Is abortion permissible?\n"
            "assistant: Abortion is not permitted after implantation except when the "
            "mother's life is in danger...\n\n"
            "Latest question: what about for women with health risks?"
        ),
    },
    {
        "role": "assistant",
        "content": "Is abortion permissible for women with health risks?",
    },
    {
        "role": "user",
        "content": (
            "Conversation:\n"
            "user: Is abortion permissible?\n"
            "assistant: Abortion is not permitted after implantation...\n\n"
            "Latest question: What are the conditions for Friday prayer?"
        ),
    },
    {
        "role": "assistant",
        "content": "What are the conditions for Friday prayer?",
    },
]


def _format_turns(history: Sequence[dict]) -> str:
    lines = []
    for turn in list(history)[-HISTORY_TURNS:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        # Assistant answers are truncated: only enough to establish the topic is needed,
        # and full answers would dominate the rewrite prompt.
        if role == "assistant" and len(content) > 300:
            content = content[:300] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def needs_no_rewrite(question: str, history: Sequence[dict] | None) -> bool:
    """Cases where calling the model cannot help, so the latency is not worth paying."""
    if not history:
        return True
    if len(question) > MAX_REWRITE_CHARS:
        return True
    return not any(t.get("role") == "user" for t in history)


def rewrite_query(
    question: str, history: Sequence[dict] | None, *, timeout: float = 8.0
) -> tuple[str, bool]:
    """Return (query_for_retrieval, was_rewritten).

    Only the retrieval query is rewritten; generation still receives the user's original
    wording, so phrasing and tone are preserved. Chat history is still passed to the answer
    model, which is what lets it resolve pronouns like "it" in the original question.

    Set REWRITE_QUERY=0 to disable, in which case follow-up context relies solely on the
    prior passages replayed by the client.

    Failures are non-fatal: retrieval falls back to the original question rather than
    breaking the request, since a degraded query beats no answer.
    """
    question = question.strip()
    if not REWRITE_ENABLED:
        return question, False
    if needs_no_rewrite(question, history):
        return question, False

    try:
        from rag.groq_client import get_client

        if not os.getenv("GROQ_API_KEY"):
            return question, False

        messages = [{"role": "system", "content": SYSTEM}, *FEWSHOT]
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Conversation:\n{_format_turns(history)}\n\n"
                    f"Latest question: {question}"
                ),
            }
        )

        kwargs = {
            "model": REWRITE_MODEL,
            "messages": messages,
            "temperature": 0,
            "max_completion_tokens": REWRITE_MAX_TOKENS,
            "stream": False,
        }
        # gpt-oss reasons by default, which cost ~1.5s on this trivial task; 'low' brings it
        # to ~350ms with no loss of correctness. Groq rejects 'none', so 'low' is the floor.
        if "gpt-oss" in REWRITE_MODEL:
            kwargs["reasoning_effort"] = REWRITE_REASONING_EFFORT

        completion = get_client(timeout).chat.completions.create(**kwargs)
        rewritten = (completion.choices[0].message.content or "").strip()

        # Guard against a model that ignores instructions and returns prose or nothing.
        if not rewritten or len(rewritten) > MAX_REWRITE_CHARS * 2:
            return question, False
        rewritten = rewritten.strip().strip('"').strip()
        if not rewritten:
            return question, False

        return rewritten, rewritten.lower() != question.lower()
    except Exception:
        return question, False



def translate_query_to_english(query: str) -> str:
    """Translate non-English queries to English for better retrieval.
    
    The corpus is in English, so Hindi/Gujarati/Urdu queries won't match BM25 keywords.
    This translates the query while preserving intent and key terms.
    """
    # Skip translation if query contains common English Islamic terms
    english_indicators = [
        "what", "is", "are", "the", "how", "when", "why", "where", "can", "do", "does",
        "prayer", "fasting", "zakat", "hajj", "wudu", "ghusl", "prohibited", "allowed",
        "permissible", "ruling", "marriage", "divorce", "inheritance",
    ]
    
    lower = query.lower()
    # If query has 2+ English indicator words, it's probably already English
    matches = sum(1 for word in english_indicators if f" {word} " in f" {lower} " or lower.startswith(word + " ") or lower.endswith(" " + word))
    if matches >= 2:
        return query
    
    # Hindi/Urdu/Gujarati indicators (written in Latin/Devanagari)
    hindi_guj_indicators = [
        # Hindi/Urdu common question words & verbs
        "kya", "mai", "mein", "kar", "karu", "kare", "karein", "ke", "ki", "liye", "liya",
        "kis", "kaise", "kaun", "kab", "kahan", "kyun", "hoon", "hai", "hain", "tha", "the",
        "aur", "ko", "se", "tak", "par", "mein", "pe", "ka", "koi", "yeh", "woh", "agar",
        "toh", "phir", "kuch", "sab", "sabhi", "kitna", "jab", "jo", "bhi",
        # Gujarati-specific (romanized)
        "shu", "chhe", "che", "chey", "tame", "ame", "ema", "emane", "karva", "karvu", "kevi",
        "kevu", "mate", "kyare", "ketla", "ketli", "kya", "kone", "ane", "pan", "thi", "ma",
        "nu", "ne", "na", "ni", "nathi", "nai", "java", "aave", "ave", "joi", "joie",
    ]
    hindi_matches = sum(1 for word in hindi_guj_indicators if word in lower)
    
    # If 2+ Hindi words detected or query has non-Latin script, translate
    has_non_latin = any(ord(c) > 0x024F for c in query)
    
    if hindi_matches < 2 and not has_non_latin:
        return query  # Probably English or ambiguous — pass through
    
    from rag.providers import default_provider, gemini_generate, groq_generate
    
    system = """You translate non-English queries about Islamic law into clear, \
search-friendly English. Output the complete translation. Be precise with religious terms.

Examples:
- "kya mai muth maar sakta hoon" → "is masturbation allowed in Islam"
- "namaz ke liye wazu kaise karein" → "how to perform wudu for prayer"
- "roza kis waqt toot jata hai" → "what breaks a fast"
- "nikah ki sharait kya hain" → "what are the conditions for marriage"
- "mane kem khbr pade hu baaligh chu k nahi" → "how can I know if I have reached puberty"
"""
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Query: {query}\n\nEnglish translation:"},
    ]
    
    provider = default_provider()
    if provider == "groq":
        result = groq_generate(messages, max_tokens=120, temperature=0.3, reasoning_effort="low")
    else:
        result = gemini_generate(messages, max_tokens=120, temperature=0.3)
    
    return result.strip().strip('"').strip().replace("English translation:", "").strip()
