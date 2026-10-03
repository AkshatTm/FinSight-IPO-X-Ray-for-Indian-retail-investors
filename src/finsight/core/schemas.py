"""Core pydantic schemas (02_ARCHITECTURE.md section 6, aligned with 06_API_CONTRACT.md).

Every extracted value carries a ``kind`` discriminator so a union of value types
round-trips through JSON unambiguously. Money is serialised as a decimal string
(never a float). Pages are PDF pages, 1-indexed (ADR-025); ``printed_page`` is the
number printed on the page, when one can be read.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, PlainSerializer, WithJsonSchema

BBox = tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points
DocType = Literal["rhp", "drhp", "prospectus"]
# Detection result only; "unknown" is never stored (B02 §5).
DetectedType = Literal["rhp", "drhp", "prospectus", "unknown"]
Verdict = Literal["verified", "unverifiable", "contradicted"]
Language = Literal["en", "hi"]

# Decimals travel as strings ("8000000000.00") so no float ever touches money (06 conventions).
DecimalStr = Annotated[
    Decimal,
    PlainSerializer(str, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "examples": ["8000000000.00"]}),
]

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
    value_inr: DecimalStr | None
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
    value: DecimalStr
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
    # The line the value is printed in and the character span of the value inside it, stored with
    # the box so the API never has to open the parsed document to answer an X-Ray request.
    sentence: str | None = None
    sentence_hit: tuple[int, int] | None = None
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


class BidClosed(BaseModel):
    """The "bid/offer closed on" date printed on the Prospectus cover, with its page."""

    closed_on: date
    page: int  # PDF page of the Prospectus
    text: str  # the words it was read from


class XRay(BaseModel):
    ipo_id: str
    company: str
    built_at: datetime
    fields: list[FieldResult]
    derived: dict[str, str]  # decimal strings, as in 06
    bid_closed: BidClosed | None = None  # from the Prospectus; absent in older X-Rays
    # True when the build looked for each value's box and sentence: a candidate without a box then
    # has none to find, and the API must not open the parsed documents to look again.
    boxes_located: bool = False


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


# --------------------------------------------------------------------------- risks (Phase 2)
RiskCategory = Literal[
    "financial",
    "debt_liquidity",
    "customers_suppliers",
    "competition",
    "legal_litigation",
    "regulatory",
    "promoters_governance",
    "operations",
    "technology_data",
    "market_macro",
]
SimpleStatus = Literal["pending", "ready", "rejected", "failed"]
Seriousness = Literal["high", "medium", "low"]
Status3 = Literal["ok", "watch", "concern", "not_available", "not_applicable"]
Level = Literal["low", "medium", "high"]


class RedFlag(BaseModel):
    """One of the 13 red-flag checks (B01 §5, B02 §5); ``points`` 2 concern, 1 watch, else 0."""

    id: str
    title: str
    status: Status3
    sentence: str
    numbers_used: dict[str, str] = Field(default_factory=dict)
    evidence: list[PageEvidence] = Field(default_factory=list)
    rule: str = ""
    points: int = 0


class RedFlags(BaseModel):
    """``redflags.json`` (B06 §3 ``/redflags``)."""

    flags: list[RedFlag] = Field(default_factory=list)
    financial_company: bool = False  # lenders: debt checks are "not applicable"
    thresholds_version: str = ""


class RiskLevelReason(BaseModel):
    source: Literal["redflag", "risk"]
    id: str
    label: str
    points: int
    link: str  # "#redflag-RF03" or "#risk-r12": the report anchors (B05 §5.3)


class RiskLevel(BaseModel):
    """B02 §7.4: points over the checks available, placed among past IPOs (2018-2023)."""

    level: Level
    points: int
    max_points: int
    score: float  # points / max_points
    percentile: float  # share of reference IPOs with a lower score (0-100)
    checks_available: int
    reasons: list[RiskLevelReason]
    thresholds: dict[str, float]
    corpus_n: int
    provisional: bool  # thresholds are placeholders until B2.6b
    behind_click: bool
    disclaimer_key: str = "risklevel.disclaimer"


class Hedging(BaseModel):
    """B02 §7.2: hedge words counted, and whether the risk states a past fact with a number."""

    hedge_count: int = 0
    hard_fact: bool = False
    flag: bool = False  # hedge_count >= 3 and hard_fact: "written cautiously, but it happened"
    fact_sentence: str | None = None


class NearestExample(BaseModel):
    company: str
    year: int
    title: str
    similarity: float


class Risk(BaseModel):
    """One risk factor of a document (B02 §5); features are ``None`` until their stage runs."""

    rid: str
    order: int
    title: str
    body: str
    page_start: int
    page_end: int
    group: str | None = None  # "Internal risks", "External risks", "Risks relating to the Offer"
    category: RiskCategory | None = None
    category_conf: float | None = None
    novelty: float | None = None  # share of past IPOs with a similar risk (0-1); low = unusual
    nearest_examples: list[NearestExample] = Field(default_factory=list)
    hedging: Hedging = Field(default_factory=Hedging)
    numbers: list[Amount] = Field(default_factory=list)
    seriousness: Seriousness | None = None
    importance: float | None = None
    simple: str | None = None
    simple_status: SimpleStatus = "pending"
    simple_checks: list[CheckResult] = Field(default_factory=list)


# --------------------------------------------------------------------------- compare (Phase 2)
CompareMetric = Literal["issue_size_inr", "ofs_share", "insider_price_gap", "pe"]


class Peer(BaseModel):
    """One row of the Basis for Offer Price peer table (B05 §5.6). ``None`` = not stated."""

    name: str
    pe: DecimalStr | None = None
    eps: DecimalStr | None = None  # basic EPS, ₹
    ronw: DecimalStr | None = None  # return on net worth, %
    nav: DecimalStr | None = None  # net asset value (book value) per share, ₹
    is_issuer: bool = False
    evidence: PageEvidence | None = None


class ComparePercentile(BaseModel):
    metric: CompareMetric
    value: float
    percentile: float  # share (0-100) of reference IPOs with a lower value
    corpus_n: int


class Compare(BaseModel):
    """``compare.json`` (B02 §3.1 stage 14, B06 ``/compare``)."""

    peers: list[Peer] = Field(default_factory=list)
    peer_median_pe: DecimalStr | None = None
    percentiles: list[ComparePercentile] = Field(default_factory=list)
    provisional: bool = True  # reference quantiles are placeholders until computed on the corpus


# --------------------------------------------------------------------------- uploads (Phase 2)
RejectionCode = Literal[
    "scanned", "password", "too_large", "too_many_pages", "not_offer_document", "hash_mismatch"
]
DocStatus = Literal["uploading", "processing", "ready", "partial", "failed"]


class PageEvidence(BaseModel):
    """Where a value or risk came from: a page, optionally a box and the sentence."""

    doc_id: str
    page: int = Field(ge=1)
    bbox: BBox | None = None
    sentence: str | None = None


class DocRecord(BaseModel):
    """One uploaded or showcase document, keyed by ``doc_id`` (B02 §5).

    ``doc_type``, ``company`` and ``pages`` are filled in by the ``detected`` stage, so they are
    empty while the job is queued. A rejected upload keeps its ``rejection`` code.
    """

    doc_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    doc_type: DocType | None = None
    company: str | None = None
    pages: int | None = Field(default=None, ge=1)
    uploaded_by: str | None = None
    is_showcase: bool = False
    companion_of: str | None = None
    created_at: datetime
    status: DocStatus = "processing"
    rejection: RejectionCode | None = None


JobStatus = Literal["queued", "running", "done", "failed"]


class Job(BaseModel):
    """One processing run of a document (B02 §5)."""

    job_id: str
    doc_id: str
    stage: str
    status: JobStatus
    progress: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
