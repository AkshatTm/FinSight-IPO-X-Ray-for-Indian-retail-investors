"""Page clean-up rules: repeated headers/footers, printed page numbers, scanned pages.

All pure functions on plain strings and counts, so they are easy to test.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

# A line only counts as header/footer if it sits in the top or bottom band of the page.
EDGE_BAND = 0.12
# ... and appears (digits masked) on more than this share of pages (02 section 10.1, rule 5).
BOILERPLATE_SHARE = 0.5
# A page with fewer extracted characters than this but with images is a scan (rule 6).
SCANNED_MAX_CHARS = 50

_ROMAN = re.compile(r"^(?=[ivxlcdm]+$)m{0,3}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$")
_PAGE_NUMBER = re.compile(r"^(?:page\s+)?(\d{1,4}|[ivxlcdm]{1,8})$", re.IGNORECASE)


def line_key(line: str) -> str:
    """Normalise a line for repeat detection: lowercase, digits -> '#', single spaces."""
    return " ".join(re.sub(r"\d+", "#", line.lower()).split())


def boilerplate_keys(page_edge_lines: Iterable[Iterable[str]]) -> set[str]:
    """Keys of edge lines that repeat on more than half of the pages."""
    pages = [set(map(line_key, lines)) for lines in page_edge_lines]
    if len(pages) < 3:
        return set()
    counts = Counter(key for keys in pages for key in keys if key)
    return {key for key, n in counts.items() if n / len(pages) > BOILERPLATE_SHARE}


def read_printed_page(footer_lines: Iterable[str]) -> str | None:
    """The page number printed in the footer ('12', 'xiv', 'Page 7'), if one is there."""
    for line in footer_lines:
        match = _PAGE_NUMBER.match(line.strip())
        if not match:
            continue
        value = match.group(1)
        if value.isdigit() or _ROMAN.match(value.lower()):
            return value.lower() if not value.isdigit() else value
    return None


def is_scanned_page(n_chars: int, n_images: int) -> bool:
    """Almost no text but at least one image: a scanned page we cannot read without OCR."""
    return n_chars < SCANNED_MAX_CHARS and n_images > 0
