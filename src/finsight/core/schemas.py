"""Core pydantic schemas (02_ARCHITECTURE.md section 6, aligned with 06_API_CONTRACT.md).

Every extracted value carries a ``kind`` discriminator so a union of value types
round-trips through JSON unambiguously. Money is serialised as a decimal string
(never a float). Pages are PDF pages, 1-indexed (ADR-025); ``printed_page`` is the
number printed on the page, when one can be read.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

BBox = tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points
DocType = Literal["rhp", "prospectus"]
Verdict = Literal["verified", "unverifiable", "contradicted"]
Language = Literal["en", "hi"]

# Reason codes for verifier checks (02 section 10.3) and X-Ray fields (06 xray).
ReasonCode = Literal[
    "verified",
    "scale_mismatch",
    "wrong_value",
    "wrong_metric",
    "not_found",
    "placeholder",
    "section_not_found",
    "extractors_disagree",
    "not_in_document",
]


# --------------------------------------------------------------------------- documents
class Word(BaseModel):
    text: str
    bbox: BBox
    font_size: float
    bold: bool


class Page(BaseModel):
    number: int  # PDF page, 1-indexed
    printed_page: str | None = None
    width: float
    height: float
    words: list[Word]
    text: str
    is_scanned: bool


class ParsedDoc(BaseModel):
    ipo_id: str
    doc_type: DocType
    source_path: str
    n_pages: int
    pages: list[Page]
    sha256: str


class Section(BaseModel):
    id: str
    title: str
    start_page: int
    end_page: int
    method: Literal["toc", "regex", "font"]
    confidence: float


class TableCell(BaseModel):
    row: int
    col: int
    text: str
    bbox: BBox
    page: int


class Table(BaseModel):
    id: str
    section_id: str
    pages: list[int]
    header_scale: str | None = None  # e.g. "₹ in million"
    cells: list[TableCell]


class Passage(BaseModel):
    id: str  # <ipo_id>:p<page_start>:c<k>
    ipo_id: str
    doc_type: DocType
    section_id: str
    page_start: int
    page_end: int
    text: str
    # (start, end, page, box) spans; required because "Show in document" needs them.
    char_to_bbox: list[tuple[int, int, int, BBox]]


# --------------------------------------------------------------------------- values
class Money(BaseModel):
    kind: Literal["money"] = "money"
    value_inr: Decimal | None
    currency: Literal["INR", "USD", "OTHER"]
    raw: str
    scale_word: str | None = None
    precision: int


class Count(BaseModel):
    kind: Literal["count"] = "count"
    value: int
    raw: str
    unit: str | None = None  # e.g. "equity shares"


class Percent(BaseModel):
    kind: Literal["percent"] = "percent"
    value: Decimal
    raw: str
    is_bps: bool = False


class Placeholder(BaseModel):
    """A blank the document fills in later: [●] or [•]. Never a zero."""

    kind: Literal["placeholder"] = "placeholder"
    raw: str


class Range(BaseModel):
    kind: Literal["range"] = "range"
    low: Money
    high: Money
    raw: str


class TextValue(BaseModel):
    kind: Literal["text"] = "text"
    text: str


class ListValue(BaseModel):
    kind: Literal["list"] = "list"
    items: list[str]


class TableValue(BaseModel):
    kind: Literal["table"] = "table"
    columns: list[str]
    rows: list[list[str]]


Amount = Annotated[Money | Count | Percent | Placeholder | Range, Field(discriminator="kind")]
Value = Annotated[
    Money | Count | Percent | Placeholder | Range | TextValue | ListValue | TableValue,
    Field(discriminator="kind"),
]


# --------------------------------------------------------------------------- extraction
class FieldSpec(BaseModel):
    id: str
    label_en: str
    label_hi: str
    type: str
    doc: DocType
    sections: list[str]
    questions: list[str]
    extractor: str
    fallback: str | None = None
    ladder: bool = True
    demo: bool = True


class Candidate(BaseModel):
    field_id: str
    extractor: str
    doc_type: DocType
    raw: str
    value: Value | None
    page: int
    printed_page: str | None = None
    bbox: BBox | None = None
    score: float
    passage_id: str | None = None


class CheckResult(BaseModel):
    check: str
    status: Verdict
    reason_code: ReasonCode
    reason: str
    answer_value: Amount | None = None
    evidence_value: Amount | None = None
    evidence_passage_id: str | None = None
    evidence_char_span: tuple[int, int] | None = None


class FieldResult(BaseModel):
    field_id: str
    chosen: Candidate | None
    candidates: list[Candidate]
    verdict: Verdict
    reason_code: ReasonCode
    reason: str
    checks: list[CheckResult]


class XRay(BaseModel):
    ipo_id: str
    company: str
    built_at: datetime
    fields: list[FieldResult]
    derived: dict[str, str]  # decimal strings, as in 06


# --------------------------------------------------------------------------- chat
class Claim(BaseModel):
    sentence: str
    char_span: tuple[int, int]
    amounts: list[Amount]
    cited: list[int]


class ChatAnswer(BaseModel):
    trace_id: str
    text: str
    language: Language
    citations: list[int]
    verdicts: list[CheckResult]
    score: float | None
    abstained: bool
    blocked: bool


class Trace(BaseModel):
    trace_id: str
    question: str
    stages: list[dict[str, object]]
    passages: list[dict[str, object]]
    prompt: str
    checks: list[CheckResult]
    timings_ms: dict[str, int]
