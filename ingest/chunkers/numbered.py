"""Chunker for documents whose atomic unit is a numbered marker at line start.

Covers three documents that share the same shape (marker + heading hierarchy above it):
  - Islamic Laws 4th ed.   'Ruling N.'   chapter=16.1pt, section=13.4pt
  - Summary of Worship     'Issue N:'    chapter=14.0pt, section=13.0pt
  - Hajj Rituals           'Rule N:'     heading=24.0pt (single level)

Text preceding the first marker under a heading is kept as a lead-in chunk, since in
Hajj Rituals especially it carries substantive context rather than boilerplate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ingest.base import Chunk, TOKEN_CAPS, emit
from ingest.extract import (
    Line,
    clean_text,
    extract_lines,
    is_page_number,
    is_plausible_heading,
)


@dataclass
class NumberedSpec:
    doc_id: str
    path: str
    marker: re.Pattern            # must capture the number in group 1
    locator_fmt: str              # e.g. "Ruling {}"
    chapter_size: float | None
    section_size: float | None
    heading_requires_bold: bool = False
    drop_sizes: tuple[float, ...] = ()
    skip_titles: tuple[str, ...] = ()      # front-matter headings that are not real chapters
    start_page: int = 0
    running_header: re.Pattern | None = None
    size_tol: float = 0.25


SPECS: dict[str, NumberedSpec] = {
    "islamic_laws": NumberedSpec(
        doc_id="islamic_laws",
        path="data/islamic-laws-4th-edition.pdf",
        marker=re.compile(r"^Ruling\s+(\d+)\.\s*"),
        locator_fmt="Ruling {}",
        chapter_size=16.1,
        section_size=13.4,
        drop_sizes=(7.9, 9.1, 10.1),
        skip_titles=(
            "contents", "contents in brief", "foreword to the fourth edition",
            "translator's preface to the third edition",
            "translator's preface to the fourth edition", "transliteration",
            "foreword", "biography", "preface",
        ),
        start_page=20,
    ),
    "summary_worship": NumberedSpec(
        doc_id="summary_worship",
        path="data/summary-of-the-rules-of-worship.pdf",
        marker=re.compile(r"^Issue\s+(\d+):\s*"),
        locator_fmt="Issue {}",
        chapter_size=14.0,
        section_size=13.0,
        heading_requires_bold=True,
        drop_sizes=(6.5, 8.0, 10.0),
        skip_titles=("contents", "introduction"),
        start_page=3,
        running_header=re.compile(r"^\d+\s*\|\s*S\s*u\s*m\s*m\s*a\s*r\s*y"),
    ),
    "hajj_rituals": NumberedSpec(
        doc_id="hajj_rituals",
        path="data/hajj-rituals.pdf",
        marker=re.compile(r"^Rule\s+(\d+):\s*"),
        locator_fmt="Rule {}",
        chapter_size=24.0,
        section_size=None,
        drop_sizes=(11.0, 16.0),
        start_page=2,
    ),
}


def _collect_headings(lines: list[Line], spec: NumberedSpec) -> list[Line]:
    """Merge heading lines that the PDF wrapped across two lines on the same page."""
    merged: list[Line] = []
    for ln in lines:
        if (
            merged
            and merged[-1].page == ln.page
            and abs(merged[-1].size - ln.size) < spec.size_tol
            and ln.y - merged[-1].y < 40
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
    return merged


def chunk_numbered(spec: NumberedSpec) -> list[Chunk]:
    cap = TOKEN_CAPS[spec.doc_id]
    lines = extract_lines(spec.path, drop_sizes=spec.drop_sizes)

    def matches(size: float, target: float | None) -> bool:
        return target is not None and abs(size - target) < spec.size_tol

    chunks: list[Chunk] = []
    chapter: str | None = None
    section: str | None = None
    locator: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if buf:
            emit(
                chunks, spec.doc_id, " ".join(buf), cap,
                chapter=chapter, section=section, locator=locator,
            )
            buf = []

    # Pre-merge wrapped headings so a two-line chapter title is treated as one.
    heading_lines = _collect_headings(
        [l for l in lines if matches(l.size, spec.chapter_size) or matches(l.size, spec.section_size)],
        spec,
    )
    heading_text = {(l.page, l.y): l.text for l in heading_lines}
    consumed_headings: set[tuple[int, float]] = set()

    for ln in lines:
        if ln.page < spec.start_page:
            continue
        raw = ln.text.strip()
        if not raw or is_page_number(raw):
            continue
        if spec.running_header and spec.running_header.match(raw):
            continue

        key = (ln.page, ln.y)
        text_probe = clean_text(raw)
        # The marker is checked before font size because these PDFs occasionally typeset a
        # ruling in the heading size (e.g. Islamic Laws 'Ruling 989.' is set at 16.1pt);
        # trusting size alone would silently swallow that ruling as a chapter title.
        is_marker = bool(spec.marker.match(text_probe))
        heading_ok = is_plausible_heading(text_probe)
        is_chapter = matches(ln.size, spec.chapter_size) and not is_marker and heading_ok
        is_section = matches(ln.size, spec.section_size) and not is_marker and heading_ok

        if is_chapter or is_section:
            # Use the merged form if this line began a wrapped heading; skip continuations.
            if key in heading_text:
                title = clean_text(heading_text[key]).strip()
                consumed_headings.add(key)
            elif any(
                k[0] == ln.page and abs(k[1] - ln.y) < 40 and k in consumed_headings
                for k in consumed_headings
            ):
                continue
            else:
                title = clean_text(raw)

            if title.lower().strip() in spec.skip_titles:
                flush()
                chapter, section, locator = None, None, None
                continue
            flush()
            locator = None
            if is_chapter:
                chapter = title
                section = None
            else:
                section = title
            continue

        text = clean_text(raw)
        m = spec.marker.match(text)
        if m:
            flush()
            locator = spec.locator_fmt.format(m.group(1))
            buf.append(text)
        else:
            buf.append(text)

    flush()
    # Reindex after all splitting is done.
    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks


def chunk_islamic_laws() -> list[Chunk]:
    return chunk_numbered(SPECS["islamic_laws"])


def chunk_summary_worship() -> list[Chunk]:
    return chunk_numbered(SPECS["summary_worship"])


def chunk_hajj_rituals() -> list[Chunk]:
    return chunk_numbered(SPECS["hajj_rituals"])
