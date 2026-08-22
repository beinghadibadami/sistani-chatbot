"""Chunker for the Holy Quran (English translation).

Structural facts established by probing this specific PDF:
  - Every page repeats a running header at y~23.6 (10.6pt). It names the surah that *starts*
    on that page, so it is NOT a reliable "current surah" signal (a page holding the end of
    surah 54 and the start of 55 is headed 55). It is skipped by vertical position.
  - A surah's real start is the 10.6pt body title at y~54, wrapped across two lines:
    '1. THE OPENING ' then '(al-Fatihah) '. This is the authoritative boundary.
  - Verse-opening lines carry a Garamond-Bold span (the bold verse number); continuation
    lines are pure MinionPro-Regular. Detecting verses by font is more reliable than regex,
    since a wrapped line can also begin with a digit.
  - Words hyphenate across line breaks ('Mer-' + 'ciful'), so trailing hyphens are joined
    without a space. This is checked on raw text before punctuation normalisation, because
    normalisation maps en/em dashes onto '-' and would otherwise cause false joins.

A single verse is too small to retrieve on its own, so consecutive verses are grouped up to
the token cap, never across a surah boundary, and each chunk records its exact verse range.
"""

from __future__ import annotations

import re

from ingest.base import Chunk, TOKEN_CAPS, count_tokens, emit, normalize_ws
from ingest.extract import Line, clean_text, extract_lines

PATH = "data/Holy-Quran-English.pdf"
DOC_ID = "quran"
BODY_START_PAGE = 11        # pages 0-10 are cover, dedication, and the CHAPTERS-SURAS index
HEADER_MAX_Y = 40.0         # running header sits at y~23.6
TITLE_SIZE = 10.6
VERSE_SIZE = 10.0
SIZE_TOL = 0.25

_TITLE_NUM = re.compile(r"^(\d{1,3})\.\s+([A-Z][A-Z'\u2019\-\s,]*?)\s*$")
_TITLE_FULL = re.compile(r"^(\d{1,3})\.\s+([A-Z][A-Z'\u2019\-\s,]*?)\s*\(([^)]+)\)\s*$")
_PAREN_NAME = re.compile(r"^\(([^)]+)\)\s*$")
_VERSE_NUM = re.compile(r"^(\d{1,3})\.\s*")
_BISMILLAH = re.compile(r"^(In the name of Allah|the Gracious, the Merciful)\s*,?\s*$", re.I)


def _near(a: float, b: float) -> bool:
    return abs(a - b) < SIZE_TOL


def chunk_quran(path: str = PATH) -> list[Chunk]:
    cap = TOKEN_CAPS[DOC_ID]
    lines = [
        l for l in extract_lines(path)
        if l.page >= BODY_START_PAGE and l.y > HEADER_MAX_Y and l.text.strip()
    ]

    chunks: list[Chunk] = []
    surah_num: int | None = None
    surah_name: str | None = None
    pending_title: tuple[int, str] | None = None   # title seen, awaiting its '(name)' line
    verses: list[tuple[int, list[str]]] = []

    def flush_surah() -> None:
        nonlocal verses
        if verses and surah_num is not None:
            _emit_surah(chunks, verses, surah_num, surah_name or "", cap)
        verses = []

    for ln in lines:
        raw = ln.text.strip()

        # --- surah title (10.6pt), possibly wrapped over two lines ---
        if _near(ln.size, TITLE_SIZE):
            m_full = _TITLE_FULL.match(raw)
            if m_full:
                flush_surah()
                surah_num = int(m_full.group(1))
                surah_name = m_full.group(3).strip()
                pending_title = None
                continue
            m_num = _TITLE_NUM.match(raw)
            if m_num:
                pending_title = (int(m_num.group(1)), m_num.group(2).strip())
                continue
            m_paren = _PAREN_NAME.match(raw)
            if m_paren and pending_title is not None:
                flush_surah()
                surah_num = pending_title[0]
                surah_name = m_paren.group(1).strip()
                pending_title = None
                continue
            continue

        if not _near(ln.size, VERSE_SIZE):
            continue
        if _BISMILLAH.match(raw):
            continue
        if surah_num is None:
            continue

        is_verse_start = ln.has_font("Garamond-Bold") and _VERSE_NUM.match(raw)
        if is_verse_start:
            m = _VERSE_NUM.match(raw)
            vnum = int(m.group(1))
            body = raw[m.end():]
            verses.append((vnum, [body]))
        elif verses:
            verses[-1][1].append(raw)

    flush_surah()
    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks


def _stitch(parts: list[str]) -> str:
    """Join a verse's wrapped lines, repairing words split by a trailing hyphen."""
    out = ""
    for part in parts:
        piece = part.rstrip()
        if not out:
            out = piece
            continue
        if out.endswith("-") and not out.endswith("--"):
            out = out[:-1] + piece.lstrip()
        else:
            out = f"{out} {piece.lstrip()}"
    return clean_text(normalize_ws(out))


def _emit_surah(
    chunks: list[Chunk],
    verses: list[tuple[int, list[str]]],
    surah_num: int,
    surah_name: str,
    cap: int,
) -> None:
    """Group consecutive verses into chunks that stay under `cap` tokens."""
    label = f"Surah {surah_num} {surah_name}".strip()
    rendered = [(vnum, f"{vnum}. {_stitch(parts)}") for vnum, parts in verses]

    group: list[tuple[int, str]] = []
    for vnum, unit in rendered:
        candidate = group + [(vnum, unit)]
        # Measure the joined body, not the sum of parts, so the emitted chunk cannot
        # overshoot the cap and get re-split into orphan fragments.
        if group and count_tokens(" ".join(u for _, u in candidate)) > cap:
            _emit_group(chunks, group, label, surah_num, cap)
            group = [(vnum, unit)]
        else:
            group = candidate
    if group:
        _emit_group(chunks, group, label, surah_num, cap)


def _emit_group(
    chunks: list[Chunk],
    group: list[tuple[int, str]],
    label: str,
    surah_num: int,
    cap: int,
) -> None:
    body = " ".join(u for _, u in group)
    v_start, v_end = group[0][0], group[-1][0]
    locator = f"verse {v_start}" if v_start == v_end else f"verses {v_start}-{v_end}"
    emit(
        chunks, DOC_ID, body, cap,
        chapter=label,
        section=None,
        locator=locator,
        extra={"surah": surah_num, "verse_start": v_start, "verse_end": v_end},
    )
