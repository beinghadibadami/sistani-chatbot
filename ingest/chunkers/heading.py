"""Chunker for dialogue-style documents that have no numeric ruling markers.

  - Women's Religious Rules: chapter=14.0pt bold, subsection=13.0pt bold. Subsections are
    short and topic-scoped, so each is usually one chunk; oversized ones split at
    'Fatimah:' / 'Mother:' dialogue turns rather than mid-sentence.
  - Jurisprudence Made Easy: only one heading level exists (25.0pt 'Dialogue on X') and the
    body is continuous father-son dialogue. Splitting therefore falls back to dialogue turns
    ('*' question / '-' answer at line start) packed up to the cap. Citations for this doc
    are necessarily coarser (heading-level only) because the source carries no finer locator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ingest.base import Chunk, TOKEN_CAPS, emit, pack_units
from ingest.extract import (
    Line,
    clean_text,
    extract_lines,
    is_page_number,
    is_plausible_heading,
)


@dataclass
class HeadingSpec:
    doc_id: str
    path: str
    chapter_size: float | None
    section_size: float | None
    turn_markers: tuple[str, ...]
    heading_requires_bold: bool = False
    drop_sizes: tuple[float, ...] = ()
    skip_titles: tuple[str, ...] = ()
    start_page: int = 0
    running_header: re.Pattern | None = None
    size_tol: float = 0.25
    merge_wrapped_headings: bool = True


SPECS: dict[str, HeadingSpec] = {
    "women_rules": HeadingSpec(
        doc_id="women_rules",
        path="data/women-religious-rules.pdf",
        chapter_size=14.0,
        section_size=13.0,
        turn_markers=("Fatimah:", "Mother:", "Fa\u1e6dimah:"),
        heading_requires_bold=True,
        drop_sizes=(6.5, 7.0, 8.0, 10.0),
        skip_titles=("contents", "preface"),
        start_page=8,
        running_header=re.compile(r"^\d+\s*\|\s*Women"),
    ),
    "jurisprudence_easy": HeadingSpec(
        doc_id="jurisprudence_easy",
        path="data/jurisprudence-made-easy.pdf",
        chapter_size=25.0,
        section_size=None,
        turn_markers=("*", "-"),
        drop_sizes=(11.0, 16.0),
        skip_titles=(
            "translator's foreword", "preface to the english edition",
            "introduction to the arabic edition", "preamble",
        ),
        start_page=15,   # first substantive heading ('Dialogue on Taqleed'); earlier pages are front matter
    ),
}


def _merge_wrapped(lines: list[Line], tol: float) -> dict[tuple[int, float], str]:
    """Map the first line of each wrapped heading to its full merged text."""
    merged: list[Line] = []
    for ln in lines:
        if (
            merged
            and merged[-1].page == ln.page
            and abs(merged[-1].size - ln.size) < tol
            and ln.y - merged[-1].y < 45
        ):
            merged[-1] = Line(
                text=f"{merged[-1].text.strip()} {ln.text.strip()}",
                size=merged[-1].size,
                bold=merged[-1].bold,
                page=merged[-1].page,
                y=merged[-1].y,
            )
        else:
            merged.append(ln)
    return {(l.page, l.y): l.text for l in merged}


def _split_turns(text: str, markers: tuple[str, ...]) -> list[str]:
    """Split a block into dialogue turns so packing never cuts mid-exchange."""
    if not markers:
        return [text]
    lines = text.split("\n")
    turns: list[str] = []
    cur: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        starts_turn = any(
            s.startswith(m) if m in ("*", "-") else s.startswith(m) for m in markers
        )
        if starts_turn and cur:
            turns.append(" ".join(cur))
            cur = []
        cur.append(s)
    if cur:
        turns.append(" ".join(cur))
    return turns or [text]


def chunk_heading(spec: HeadingSpec) -> list[Chunk]:
    cap = TOKEN_CAPS[spec.doc_id]
    lines = extract_lines(spec.path, drop_sizes=spec.drop_sizes)

    def matches(size: float, target: float | None) -> bool:
        return target is not None and abs(size - target) < spec.size_tol

    heading_candidates = [
        l for l in lines
        if (matches(l.size, spec.chapter_size) or matches(l.size, spec.section_size))
        and (l.bold or not spec.heading_requires_bold)
    ]
    merged_map = _merge_wrapped(heading_candidates, spec.size_tol) if spec.merge_wrapped_headings else {}
    candidate_keys = {(l.page, l.y) for l in heading_candidates}

    chunks: list[Chunk] = []
    chapter: str | None = None
    section: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        block = "\n".join(buf)
        turns = _split_turns(block, spec.turn_markers)
        for piece in pack_units(turns, cap):
            emit(chunks, spec.doc_id, piece, cap, chapter=chapter, section=section)
        buf = []

    for ln in lines:
        if ln.page < spec.start_page:
            continue
        raw = ln.text.strip()
        if not raw or is_page_number(raw):
            continue
        if spec.running_header and spec.running_header.match(raw):
            continue

        key = (ln.page, ln.y)
        bold_ok = ln.bold or not spec.heading_requires_bold
        heading_ok = is_plausible_heading(clean_text(raw))
        is_chapter = matches(ln.size, spec.chapter_size) and bold_ok and heading_ok
        is_section = matches(ln.size, spec.section_size) and bold_ok and heading_ok

        if is_chapter or is_section:
            if key in merged_map:
                title = clean_text(merged_map[key]).strip()
            elif key in candidate_keys:
                continue    # continuation line already folded into the merged heading
            else:
                title = clean_text(raw)
            if title.lower().strip() in spec.skip_titles:
                flush()
                chapter, section = None, None
                continue
            flush()
            if is_chapter:
                chapter = title
                section = None
            else:
                section = title
            continue

        buf.append(clean_text(raw))

    flush()
    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks


def chunk_women_rules() -> list[Chunk]:
    return chunk_heading(SPECS["women_rules"])


def chunk_jurisprudence_easy() -> list[Chunk]:
    return chunk_heading(SPECS["jurisprudence_easy"])
