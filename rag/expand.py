"""Domain query expansion for the lexical (BM25) side of retrieval.

These documents mix English with transliterated Arabic, and the same concept appears under
several surface forms: the Quran translation says "Congregation Day" where a fiqh manual says
"Friday prayer", and rulings say "wuduh" where a user types "ablution". BM25 matches literal
tokens, so without expansion those never connect.

This is deliberately a cheap fix. The alternative for closing that gap is a larger embedding
model or a cross-encoder, both of which are unaffordable on a 0.1-CPU host; a static synonym
map costs nothing at query time.

Expansion is applied only to the BM25 query. The dense query is left untouched, because the
embedding model handles paraphrase itself and padding the text with synonyms would blur it.
"""

from __future__ import annotations

import re

# Bidirectional concept groups: matching any term contributes all the others.
SYNONYM_GROUPS: list[set[str]] = [
    {"friday", "jumuah", "jumu'ah", "jumah", "congregation", "juma"},
    {"prayer", "prayers", "salah", "salat", "namaz", "salaah"},
    {"fast", "fasting", "sawm", "roza", "siyam"},
    {"ramadan", "ramadhan", "ramazan"},
    {"pilgrimage", "hajj", "umrah", "umra"},
    {"ablution", "wudu", "wuduh", "wuzu", "wudhu"},
    {"bathing", "bath", "ghusl"},
    {"tayammum", "tayamum"},
    {"zakat", "zakah", "khums"},
    {"impure", "impurity", "najis", "najasah", "najasa"},
    {"pure", "purity", "tahir", "taharah", "tahara"},
    {"menstruation", "menses", "period", "hayd", "haydh", "hayz"},
    {"postnatal", "postpartum", "nifas"},
    {"istihada", "istihadha", "istihadah"},
    {"inheritance", "inherit", "irth", "estate", "heir", "heirs"},
    {"marriage", "marry", "nikah", "mutah", "muta"},
    {"divorce", "talaq", "khula", "khul"},
    {"forbidden", "haram", "unlawful", "prohibited"},
    {"permissible", "halal", "permitted", "lawful", "allowed"},
    {"obligatory", "wajib", "compulsory"},
    {"recommended", "mustahab", "mustahabb", "sunnah"},
    {"disapproved", "makruh"},
    {"precaution", "ihtiyat"},
    {"emulation", "taqlid", "taqleed"},
    {"jurist", "mujtahid", "marja"},
    {"ruling", "fatwa", "verdict", "hukm"},
    {"corpse", "deceased", "dead", "mayyit", "janazah"},
    {"seclusion", "retreat", "itikaf", "iktikaf"},
    {"intention", "niyyah", "niyah"},
    {"prostration", "sajdah", "sujud"},
    {"bowing", "ruku"},
    {"sermon", "khutbah", "khutba"},
    {"mosque", "masjid"},
    {"charity", "sadaqah", "alms"},
    {"vow", "nadhr", "oath", "qasam"},
    {"will", "testament", "wasiyyah"},
    {"endowment", "waqf"},
    {"interest", "usury", "riba"},
    {"slaughter", "slaughtering", "dhabh", "zabiha"},
]

# term -> all expansion terms for that term
_INDEX: dict[str, set[str]] = {}
for _group in SYNONYM_GROUPS:
    for _term in _group:
        _INDEX.setdefault(_term, set()).update(_group)

_WORD = re.compile(r"[A-Za-z0-9']+")

# Cues that a question is explicitly asking for a particular kind of source. Fiqh manuals
# dominate the corpus by volume, so a question like "which *verses* describe X" otherwise
# loses to manuals that merely discuss X more often. When a cue is present the requested
# doc types are boosted during fusion, which honours the user's stated intent instead of
# letting raw term frequency decide.
DOC_INTENT: dict[str, tuple[str, ...]] = {
    "quran": ("verse", "verses", "surah", "sura", "surat", "ayah", "ayat", "quran", "qur'an", "scripture"),
    "sistani_qna": ("fatwa", "ruling", "question", "answer", "asked"),
    "islamic_laws": ("law", "laws", "ruling", "rulings"),
    "hajj_rituals": ("hajj", "pilgrimage", "umrah", "ihram", "tawaf", "meqat", "arafat", "mina"),
    "women_rules": ("menstruation", "hayd", "nifas", "istihada", "woman", "women"),
}


def detect_doc_intent(question: str) -> set[str]:
    """Return doc_ids the question explicitly asks for, if any."""
    words = {w.lower() for w in _WORD.findall(question)}
    return {doc for doc, cues in DOC_INTENT.items() if words & set(cues)}

# Words that add no retrieval signal but would pull in noise once OR-ed together.
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "of", "to", "in",
    "on", "at", "for", "with", "by", "from", "as", "and", "or", "but", "if", "then", "than",
    "that", "this", "these", "those", "it", "its", "what", "which", "who", "whom", "whose",
    "when", "where", "why", "how", "can", "could", "should", "would", "will", "shall", "may",
    "might", "must", "do", "does", "did", "have", "has", "had", "i", "you", "he", "she",
    "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "their", "our",
    "about", "any", "some", "there", "here", "please", "tell", "know", "get",
}


def expand_terms(question: str, max_terms: int = 48) -> list[str]:
    """Return deduplicated lexical search terms for `question`, including synonyms."""
    words = [w.lower() for w in _WORD.findall(question)]
    kept = [w for w in words if len(w) > 1 and w not in STOPWORDS]

    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        if term not in seen:
            seen.add(term)
            terms.append(term)

    for w in kept:
        add(w)
    # Synonyms are appended after the literal terms so that, if the cap truncates,
    # the user's own wording is never the part that gets dropped.
    for w in kept:
        for syn in sorted(_INDEX.get(w, ())):
            add(syn)

    return terms[:max_terms]


def expanded_fts_query(question: str) -> str:
    """Build an FTS5 MATCH expression from the expanded terms."""
    terms = expand_terms(question)
    if not terms:
        return ""
    return " OR ".join(f'"{t}"' for t in terms)
