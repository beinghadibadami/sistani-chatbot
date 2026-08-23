"""Cheap local question classification: does this query need RAG retrieval?

Called BEFORE retrieval, not after. This determines whether to run the full embedding +
FAISS + BM25 pipeline at all. For greetings, small talk, and thank-yous, retrieval is
pointless and the results are confusing (showing "Ruling 1125" in response to "salam").

This is deliberately a static-rule classifier, not an LLM call, because:
  - It runs on every single request and must cost zero latency.
  - The distinction is simple: does the question plausibly ask about Islamic practice?
  - False negatives (classifying a real question as small-talk) are far worse than
    false positives (retrieving for a greeting). So the default is "needs retrieval"
    and only clearly non-Islamic patterns skip it.

Classification:
  NEEDS_RAG    → run full retrieval, pass chunks to the LLM
  SKIP_RAG     → send to LLM with no context (greeting, thanks, "what can you do")
  BLOCK        → off-topic, LLM will decline (still no retrieval needed)
"""

from __future__ import annotations

import re
from enum import Enum


class QueryIntent(Enum):
    NEEDS_RAG = "needs_rag"
    SKIP_RAG = "skip_rag"     # greeting/thanks/meta — answer directly, no sources
    BLOCK = "block"           # off-topic — LLM declines, no sources


# Patterns that are clearly small-talk/greetings and never need retrieval.
# These are checked BEFORE the injection filter, because "salam" is not an attack.
_GREETING_PATTERNS = re.compile(
    r"^(as[- ]?salaa?m|salaa?m|wa[- ]?alaik|hello|hi|hey|good\s*(morning|evening|afternoon|night)"
    r"|how\s+are\s+(you|u)|thank\s*(you|s)|jazak|shukr|bye|goodbye|see\s+you"
    r"|welcome|nice\s+to\s+meet|assalamu?\s*alaikum|wa\s*alaikum)"
    r"(\s|$|[.!?,])",
    re.IGNORECASE,
)

# "what can you do" / "who are you" / "help" — meta questions about the bot itself
_META_PATTERNS = re.compile(
    r"^(what\s+(can|do)\s+you\s+do|who\s+are\s+you|help$|what\s+is\s+this"
    r"|what\s+are\s+you|tell\s+me\s+about\s+yourself)",
    re.IGNORECASE,
)

# Clearly off-topic: programming, coding, math unrelated to zakat/inheritance, etc.
_OFFTOPIC_PATTERNS = re.compile(
    r"\b(python|javascript|java|html|css|react|code|coding|programming|algorithm"
    r"|machine\s+learning|docker|kubernetes|git|github|api|database|sql"
    r"|football|soccer|cricket|basketball|tennis|movie|film|tv\s+show"
    r"|stock\s+market|bitcoin|crypto|weather\s+today|recipe\s+for"
    r"|write\s+me\s+(a\s+)?(code|script|program|email|essay|poem|story))\b",
    re.IGNORECASE,
)

# Islamic signal words — if ANY of these appear, the question is plausibly Islamic
# regardless of what else it contains (e.g. "is coding haram" is Islamic, not off-topic).
_ISLAMIC_SIGNAL = re.compile(
    r"\b(islam|islamic|muslim|quran|qur.?an|hadith|sunnah|shia|sunni|fiqh"
    r"|haram|halal|wajib|mustahab|makruh|najis|tahir|ghusl|wudu|salat|salah"
    r"|sawm|fast|hajj|umrah|zakat|khums|jihad|imam|ayatollah|sistani|marja"
    r"|fatwa|ruling|sharia|nikah|talaq|mut.?ah|mahram|hijab|niqab|dua|dhikr"
    r"|janazah|kafan|iddah|inheritance|mosque|masjid|prayer|ramadan|eid"
    r"|allah|prophet|muhammad|ali|husain|hussein|karbala|ashura)\b",
    re.IGNORECASE,
)


def classify_query(question: str) -> QueryIntent:
    """Determine whether a question needs RAG retrieval, can be answered directly, or
    should be declined.

    Order matters:
      1. Greetings/meta → SKIP_RAG (answered warmly, no sources)
      2. Islamic signal present → NEEDS_RAG (even if it also mentions code/sports)
      3. Off-topic pattern → BLOCK (no retrieval, model declines)
      4. Default → NEEDS_RAG (ambiguous questions get retrieval; false positives are cheap)
    """
    stripped = question.strip()
    if not stripped:
        return QueryIntent.SKIP_RAG

    if _GREETING_PATTERNS.match(stripped):
        return QueryIntent.SKIP_RAG

    if _META_PATTERNS.match(stripped):
        return QueryIntent.SKIP_RAG

    # Islamic signal overrides off-topic patterns ("is coding haram" → needs RAG)
    if _ISLAMIC_SIGNAL.search(stripped):
        return QueryIntent.NEEDS_RAG

    if _OFFTOPIC_PATTERNS.search(stripped):
        return QueryIntent.BLOCK

    # Default: assume it's a jurisprudence question. Retrieval is cheap and a false
    # positive just means the model sees irrelevant context it can ignore.
    return QueryIntent.NEEDS_RAG
