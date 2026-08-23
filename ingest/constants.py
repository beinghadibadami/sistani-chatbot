"""Lightweight constants shared between build-time and run-time code.

This module must NOT import heavy build-time dependencies (tiktoken, fastembed, PyMuPDF)
so that run-time code (main.py) can import from it without pulling in those packages.
"""

DOC_TITLES = {
    "islamic_laws": "Islamic Laws (4th Edition)",
    "summary_worship": "Summary of the Rules of Worship",
    "hajj_rituals": "Hajj Rituals",
    "jurisprudence_easy": "Jurisprudence Made Easy",
    "women_rules": "Women's Religious Rules",
    "quran": "Holy Quran",
    "sistani_qna": "Sistani Q&A",
}
