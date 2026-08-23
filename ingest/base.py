"""Shared chunk schema, token counting, and the recursive text packer used by all chunkers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")

# BGE truncates input at 512 tokens. Embedding text is "citation header + body", so the
# body caps below plus HEADER_TOKEN_BUDGET must stay under that limit, otherwise chunk tails
# would be silently dropped.
BGE_INPUT_LIMIT = 512
HEADER_TOKEN_BUDGET = 32

from ingest.constants import DOC_TITLES

# Per-doc-type token caps. Legal/ruling text tolerates larger chunks because a single
# ruling is self-contained; scripture and dialogue are denser per token so they stay smaller.
TOKEN_CAPS = {
    "islamic_laws": 470,
    "summary_worship": 470,
    "hajj_rituals": 470,
    "jurisprudence_easy": 400,
    "women_rules": 400,
    "quran": 300,
    "sistani_qna": 470,
}

assert max(TOKEN_CAPS.values()) + HEADER_TOKEN_BUDGET <= BGE_INPUT_LIMIT, (
    "token caps leave no room for the contextual header within BGE's input limit"
)


def count_tokens(text: str) -> int:
    """Token count used for all chunk size caps."""
    return len(_ENC.encode(text, disallowed_special=()))


@dataclass
class Chunk:
    """One retrievable unit, carrying everything needed to cite it precisely."""

    doc_id: str
    text: str
    chapter: str | None = None
    section: str | None = None
    locator: str | None = None       # human-readable citation fragment, e.g. "Ruling 2748"
    chunk_index: int = 0             # position within the document
    part: int | None = None          # set when one semantic unit was split across chunks
    part_of: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def n_tokens(self) -> int:
        return count_tokens(self.text)

    def citation(self) -> str:
        """Assemble the display citation string shown to the user."""
        bits = [DOC_TITLES.get(self.doc_id, self.doc_id)]
        if self.chapter:
            bits.append(self.chapter)
        if self.section and self.section != self.chapter:
            bits.append(self.section)
        if self.locator:
            bits.append(self.locator)
        out = " — ".join(bits)
        if self.part and self.part_of and self.part_of > 1:
            out += f" (part {self.part}/{self.part_of})"
        return out

    def embed_header(self, budget: int = HEADER_TOKEN_BUDGET) -> str:
        """Compact provenance line prepended to the body before embedding.

        Without this the vector is computed from the body alone, so a chunk like
        "Ruling 2747. A husband and wife inherit from one another..." carries no signal that
        it belongs to the Inheritance chapter - the words "inheritance" and "Irth" never
        appear in it. Many rulings are also bare cross-references ("as stated in the previous
        rulings") and are nearly meaningless in isolation.

        The header is kept within `budget` tokens by dropping the least specific parts first,
        so the locator (the most precise identifier) always survives.
        """
        title = DOC_TITLES.get(self.doc_id, self.doc_id)
        section = self.section if self.section != self.chapter else None

        # Ordered most- to least- expendable.
        variants = [
            [title, self.chapter, section, self.locator],
            [title, self.chapter, self.locator],
            [title, self.locator],
            [title],
        ]
        for parts in variants:
            header = " | ".join(p for p in parts if p)
            if count_tokens(header) <= budget:
                return header

        # Even the title alone is over budget: hard-truncate on word boundaries.
        words = variants[-1][0].split()
        while words and count_tokens(" ".join(words)) > budget:
            words.pop()
        return " ".join(words)

    def embed_text(self) -> str:
        """The exact string that gets vectorised and indexed for BM25."""
        return f"{self.embed_header()}\n{self.text}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SENT_SPLIT = re.compile(r"(?<=[.!?\"'\u201d\u2019])\s+(?=[A-Z\u201c\u2018(])")


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def pack_units(units: Iterable[str], cap: int, joiner: str = " ") -> list[str]:
    """Greedily pack pre-split text units into groups that stay under `cap` tokens.

    A unit larger than `cap` on its own is emitted alone rather than dropped, then
    split at sentence level by `split_oversized`.
    """
    out: list[str] = []
    cur: list[str] = []
    cur_tokens = 0
    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        n = count_tokens(unit)
        if cur and cur_tokens + n > cap:
            out.append(joiner.join(cur))
            cur, cur_tokens = [], 0
        cur.append(unit)
        cur_tokens += n
    if cur:
        out.append(joiner.join(cur))
    return out


def _split_words(text: str, cap: int) -> list[str]:
    """Last-resort split of a single unsplittable sentence at word boundaries."""
    words = text.split()
    out: list[str] = []
    cur: list[str] = []
    for w in words:
        cur.append(w)
        if count_tokens(" ".join(cur)) > cap:
            if len(cur) == 1:
                out.append(w)       # single token exceeds cap; emit rather than loop
                cur = []
            else:
                cur.pop()
                out.append(" ".join(cur))
                cur = [w]
    if cur:
        out.append(" ".join(cur))
    return out


def split_oversized(text: str, cap: int) -> list[str]:
    """Split an oversized block at sentence boundaries, never mid-sentence.

    Sentence-level packing can still leave a piece over the cap when a single sentence is
    itself longer than the cap, so any remaining oversized piece is word-split afterwards.
    """
    if count_tokens(text) <= cap:
        return [text]
    sentences = split_sentences(text)
    packed = _split_words(text, cap) if len(sentences) == 1 else pack_units(sentences, cap)
    out: list[str] = []
    for piece in packed:
        if count_tokens(piece) > cap:
            out.extend(_split_words(piece, cap))
        else:
            out.append(piece)
    return out


def emit(
    chunks: list[Chunk],
    doc_id: str,
    text: str,
    cap: int,
    *,
    chapter: str | None = None,
    section: str | None = None,
    locator: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append `text` as one or more Chunks, splitting it only if it exceeds `cap`."""
    text = normalize_ws(text)
    if not text:
        return
    pieces = split_oversized(text, cap)
    total = len(pieces)
    for i, piece in enumerate(pieces, start=1):
        chunks.append(
            Chunk(
                doc_id=doc_id,
                text=piece,
                chapter=chapter,
                section=section,
                locator=locator,
                chunk_index=len(chunks),
                part=i if total > 1 else None,
                part_of=total if total > 1 else None,
                extra=dict(extra or {}),
            )
        )


def normalize_ws(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
