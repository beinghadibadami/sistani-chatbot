"""Per-document-type chunkers, each producing the shared `Chunk` schema."""

from ingest.chunkers.numbered import (
    chunk_hajj_rituals,
    chunk_islamic_laws,
    chunk_summary_worship,
)
from ingest.chunkers.qna import chunk_sistani_qna
from ingest.chunkers.quran import chunk_quran
from ingest.chunkers.heading import chunk_jurisprudence_easy, chunk_women_rules

CHUNKERS = {
    "islamic_laws": chunk_islamic_laws,
    "summary_worship": chunk_summary_worship,
    "hajj_rituals": chunk_hajj_rituals,
    "quran": chunk_quran,
    "sistani_qna": chunk_sistani_qna,
    "women_rules": chunk_women_rules,
    "jurisprudence_easy": chunk_jurisprudence_easy,
}

__all__ = ["CHUNKERS"]
