"""Cheap local pre-filter: skip retrieval for pure greetings, nothing else.

Regex cannot reliably judge "is this question off-topic?" — real phrasing is too varied
("is drinking wine haram if it's for medicine", "explain zakat simply") to be caught by
keyword lists, and a misfire there means retrieval gets skipped for a real question,
which is a genuine correctness loss (the model answers from memory instead of the corpus).

So this module does NOT attempt off-topic / scope classification. That job is already
handled reliably by the LLM itself: the system prompt instructs it to decline off-topic
requests, and `_answer_has_citation()` in main.py suppresses sources when the answer
didn't actually cite anything. Both were verified working correctly in testing without
any pre-filtering. Regex would only save one retrieval call (~300ms) on questions the
model was going to decline anyway — not worth the risk of misclassifying a real question.

The ONLY thing this module still does: skip retrieval for a pure greeting/thanks with
nothing else in the message. This is safe even when wrong, because the worst case of a
false negative here is a single wasted retrieval call — never a wrong or missing answer.
The pattern is deliberately narrow (whole message, short length) so "salam, what is
wudu?" still gets retrieval; only a bare "salam" or "thank you" skips it.
"""

from __future__ import annotations

import re
from enum import Enum

# A pure greeting/thanks is short. Capping length prevents a greeting embedded in a
# longer real question from triggering a skip (e.g. "salam, I wanted to ask about wudu").
_MAX_GREETING_WORDS = 6

_GREETING_OPENER = (
    r"as[- ]?sala+m(\s+(alaikum|alaykum))?(\s+wa\s+rahmatullah)?"
    r"|wa[- ]?alaikum(\s+as[- ]?sala+m)?"
    r"|sala+m|hel+o+|hi+|he+y+"
    r"|good\s*(morning|evening|afternoon|night)"
    r"|thank\s*(you|s)(\s+(so\s+much|very\s+much))?|jazak\s*allah(\s+khair)?|shukr(an|iya)?"
    r"|bye+|go+dbye+|see\s+you(\s+later)?|o+k+\s*(thanks?|bye+)?"
)
_GREETING_TAIL = r"how\s+are\s+(you|u)\??"

# Either a greeting phrase alone, or a greeting phrase followed by a "how are you" tail
# (a very common compound, e.g. "salam how are you") — but nothing else, so a real
# question tacked onto a greeting still falls through to NEEDS_RAG.
_PURE_GREETING = re.compile(
    rf"^(({_GREETING_OPENER})[\s.!?,]*)+({_GREETING_TAIL})?[\s.!?,]*$"
    rf"|^{_GREETING_TAIL}[\s.!?,]*$",
    re.IGNORECASE,
)


class QueryIntent(Enum):
    NEEDS_RAG = "needs_rag"   # run retrieval — the default for everything, including
                               # ambiguous and off-topic questions (the LLM handles scope)
    SKIP_RAG = "skip_rag"      # pure greeting/thanks only — answered directly, no sources


def classify_query(question: str) -> QueryIntent:
    """Skip retrieval only for a short, pure greeting/thanks. Everything else — including
    off-topic and ambiguous questions — goes through retrieval; the LLM decides scope.
    """
    stripped = question.strip()
    if not stripped:
        return QueryIntent.SKIP_RAG

    if len(stripped.split()) <= _MAX_GREETING_WORDS and _PURE_GREETING.match(stripped):
        return QueryIntent.SKIP_RAG

    return QueryIntent.NEEDS_RAG
