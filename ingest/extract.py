"""PyMuPDF extraction: structured lines carrying font metadata, plus text cleanup.

Every chunker consumes `extract_lines()`. The font metadata (size/bold) is what lets the
heading-anchored chunkers find section boundaries in documents that have no numeric markers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import fitz


@dataclass
class Line:
    text: str
    size: float          # max span size on the line
    bold: bool
    page: int
    y: float             # vertical position, used to identify running headers/footers
    fonts: tuple[str, ...] = ()

    @property
    def is_blank(self) -> bool:
        return not self.text.strip()

    def has_font(self, needle: str) -> bool:
        needle = needle.lower()
        return any(needle in f.lower() for f in self.fonts)


def extract_lines(
    path: str,
    *,
    min_size: float = 0.0,
    drop_sizes: tuple[float, ...] = (),
    size_tol: float = 0.15,
) -> list[Line]:
    """Extract every text line with its dominant font size and bold flag.

    `drop_sizes` removes footnote/page-number sizes outright, which is simpler and more
    reliable than trying to detect them positionally.
    """
    doc = fitz.open(path)
    lines: list[Line] = []
    for pno in range(doc.page_count):
        page_dict = doc[pno].get_text("dict")
        for block in page_dict["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                size = max(s["size"] for s in spans)
                if size < min_size:
                    continue
                if any(abs(size - d) < size_tol for d in drop_sizes):
                    continue
                text = "".join(s["text"] for s in spans)
                bold = any(
                    ("bold" in s["font"].lower() or "semibold" in s["font"].lower())
                    for s in spans
                )
                lines.append(
                    Line(
                        text=text,
                        size=round(size, 1),
                        bold=bold,
                        page=pno,
                        y=round(line["bbox"][1], 1),
                        fonts=tuple(sorted({s["font"] for s in spans})),
                    )
                )
    doc.close()
    return lines


# --- text cleanup -------------------------------------------------------------------

# Ligature/transliteration artefacts and smart punctuation seen in these specific PDFs.
# En/em dashes are deliberately preserved: they are meaningful punctuation here, and
# collapsing them onto '-' both hurts readability and risks colliding with the
# end-of-line hyphenation repair, which keys on a trailing ASCII '-'.
_REPLACEMENTS = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\ufb01": "fi", "\ufb02": "fl",
    "\u00fb": "\u2014",   # Islamic Laws renders an em-dash as 'û'
}


def clean_text(text: str) -> str:
    for a, b in _REPLACEMENTS.items():
        text = text.replace(a, b)
    return text


_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")


def join_lines(lines: list[str]) -> str:
    """Join extracted lines into flowing text, repairing words hyphenated across breaks.

    The Quran PDF in particular breaks words like 'or-\\nder' and 'hospital-\\nity'; left
    alone these corrupt both the embedding and the displayed text.
    """
    text = "\n".join(lines)
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    return clean_text(text)


def strip_running_header(text: str, patterns: list[re.Pattern]) -> bool:
    """True if a line matches any known running header/footer pattern."""
    stripped = text.strip()
    return any(p.match(stripped) for p in patterns)


def is_page_number(text: str) -> bool:
    return bool(re.fullmatch(r"\d{1,4}", text.strip()))


_ARABIC = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")
MAX_HEADING_CHARS = 130


def is_plausible_heading(text: str) -> bool:
    """Reject body lines that only *look* like headings by font size.

    Islamic Laws renders inline Arabic (Quranic phrases, contract formulas) at a larger
    point size than the surrounding Latin text, so a pure size threshold captured them as
    chapter titles and produced citations like "Islamic Laws - زَوّجْتُكَ ... - Ruling 2471".
    Genuine headings in these books are short Latin transliteration, so lines containing
    Arabic script or running unusually long are excluded.
    """
    stripped = text.strip()
    if not stripped:
        return False
    if _ARABIC.search(stripped):
        return False
    if len(stripped) > MAX_HEADING_CHARS:
        return False
    return True
