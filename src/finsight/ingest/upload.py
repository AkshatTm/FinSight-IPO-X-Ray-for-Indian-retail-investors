"""Upload checks: hash, validate and detect the document type of an uploaded PDF (B-FR-01).

``validate_pdf`` runs the checks in a fixed order and stops at the first failure:
size → opens as a PDF → password → page count → scanned (text density) → offer-document type.
The rejection codes are the ones in B06 §2; the UI owns the wording (B05 §3).
"""

from __future__ import annotations

import hashlib
import re
import statistics
from dataclasses import dataclass, replace
from pathlib import Path

import pymupdf

from finsight.core.config import UploadsConfig
from finsight.core.ids import make_doc_id
from finsight.core.schemas import DetectedType, DocType, RejectionCode

COVER_PAGES = 3  # the type is read from the first pages only
SCAN_SAMPLE = 30  # pages sampled for text density on long documents
TITLE_MAX_WORDS = 10
# Longest phrase first: "draft red herring prospectus" must win over "prospectus".
_TITLES: tuple[tuple[str, DocType], ...] = (
    ("draft red herring prospectus", "drhp"),
    ("red herring prospectus", "rhp"),
    ("prospectus", "prospectus"),
)
# An offer document's cover also talks about the offer itself; two distinct markers are needed.
_OFFER_MARKERS = (
    "equity shares",
    "book running lead manager",
    "registrar to the offer",
    "registrar to the issue",
    "book built",
    "companies act",
    "sebi",
    "initial public offer",
)
MIN_OFFER_MARKERS = 2
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class UploadCheck:
    """The result of ``validate_pdf``: ``ok`` with a type, or a rejection ``code``."""

    sha256: str
    doc_id: str
    size_bytes: int
    pages: int = 0
    doc_type: DocType | None = None
    code: RejectionCode | None = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        """True when the file passed every check."""
        return self.code is None


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Hex SHA-256 of a file, read in 1 MB chunks (the server recomputes it, B06 §2)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def _norm(text: str) -> str:
    return _SPACE.sub(" ", text).strip().lower()


def _cover_lines(doc: pymupdf.Document) -> list[tuple[float, str]]:
    """(font size, text) for every line on the first pages, in reading order."""
    lines: list[tuple[float, str]] = []
    for page in doc.pages(0, min(COVER_PAGES, doc.page_count)):
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = _norm("".join(span.get("text", "") for span in spans))
                if text:
                    lines.append((max(span.get("size", 0.0) for span in spans), text))
    return lines


def detect_type(doc: pymupdf.Document) -> DetectedType:
    """RHP, DRHP or Prospectus from the cover title, else ``"unknown"``.

    The title is the largest-font short line on the first three pages that starts with one of
    the phrases, so a Prospectus that mentions "the Red Herring Prospectus dated ..." in its body
    is still a Prospectus. At least two offer markers (equity shares, BRLM, SEBI, ...) must also
    appear, so a news page that mentions a prospectus is not an offer document.
    """
    lines = _cover_lines(doc)
    text = " ".join(line for _, line in lines)
    if sum(marker in text for marker in _OFFER_MARKERS) < MIN_OFFER_MARKERS:
        return "unknown"
    best: tuple[float, DocType] | None = None
    for size, line in lines:
        if len(line.split()) > TITLE_MAX_WORDS:
            continue
        for phrase, doc_type in _TITLES:
            if line.startswith(phrase):
                if best is None or size > best[0]:
                    best = (size, doc_type)
                break
    return best[1] if best else "unknown"


def _median_chars(doc: pymupdf.Document) -> float:
    n = doc.page_count
    step = max(1, n // SCAN_SAMPLE)
    counts = [len(doc[i].get_text().strip()) for i in range(0, n, step)][:SCAN_SAMPLE]
    return statistics.median(counts) if counts else 0.0


def validate_pdf(path: Path, uploads: UploadsConfig | None = None) -> UploadCheck:
    """Check an uploaded file and return its type or the first rejection code.

    Args:
        path: The uploaded file on local disk.
        uploads: Limits; defaults to ``UploadsConfig()`` (50 MB, 1,500 pages).

    Returns:
        An ``UploadCheck``; ``ok`` is true only for an RHP, DRHP or Prospectus that passed
        every check.
    """
    limits = uploads or UploadsConfig()
    size = path.stat().st_size
    digest = sha256_file(path)
    base = UploadCheck(sha256=digest, doc_id=make_doc_id(digest), size_bytes=size)
    if size > limits.max_mb * 1024 * 1024:
        return replace(base, code="too_large", detail=f"{size} bytes")
    try:
        doc = pymupdf.open(path, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError) as err:
        return replace(base, code="not_offer_document", detail=f"not a PDF: {err}")
    with doc:
        if doc.needs_pass:
            return replace(base, code="password")
        pages = doc.page_count
        if pages > limits.max_pages:
            return replace(base, pages=pages, code="too_many_pages")
        if pages == 0:
            return replace(base, code="not_offer_document", detail="no pages")
        median = _median_chars(doc)
        if median < limits.scanned_min_median_chars:
            return replace(
                base, pages=pages, code="scanned", detail=f"median {median:.0f} chars/page"
            )
        detected = detect_type(doc)
    if detected == "unknown":
        return replace(base, pages=pages, code="not_offer_document")
    return replace(base, pages=pages, doc_type=detected)
