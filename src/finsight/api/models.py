"""Request and response models for the REST endpoints (06_API_CONTRACT.md section 2).

Money is a decimal string, pages are PDF pages (1-indexed), boxes are PDF points
``[x0, y0, x1, y1]`` with the page size given so the client can scale.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

from finsight.core.schemas import BBox, DocType, Language, ReasonCode, Value, Verdict


# ------------------------------------------------------------------------- health
class ModelStatus(BaseModel):
    """Whether one model is loaded (or loads lazily on first use)."""

    name: str | None = None
    loaded: bool
    lazy: bool | None = None


class HealthResponse(BaseModel):
    """``GET /api/health``: status, profile, demo mode and model states."""

    status: Literal["ok", "warming", "degraded"]
    profile: str
    demo_mode: bool
    models: dict[str, ModelStatus]
    version: str
    git_sha: str | None = None


# ------------------------------------------------------------------------- IPOs
class IpoSummary(BaseModel):
    """A showcase IPO in the library list, with its headline sizes."""

    id: str
    company: str
    sector: str | None = None
    listing_date: date | None = None
    rhp_pages: int
    # Decimal strings; null when the documents leave the value as [●] or omit it.
    issue_size_inr: str | None = None
    fresh_inr: str | None = None
    ofs_inr: str | None = None
    xray_status: Literal["ready", "building", "missing"]


class PageSize(BaseModel):
    """Page width and height in PDF points."""

    width: float
    height: float


class SectionInfo(BaseModel):
    """A section of a document with its PDF and printed start pages."""

    id: str
    doc: DocType
    title: str
    start_page: int
    printed_start_page: str | None = None
    end_page: int


class IpoDetail(BaseModel):
    """A showcase IPO's documents: page counts, page size and sections."""

    id: str
    company: str
    rhp_pages: int
    prospectus_pages: int | None = None
    page_size: PageSize
    sections: list[SectionInfo]


# ------------------------------------------------------------------------- X-Ray
class FieldCheck(BaseModel):
    """One verifier check on an X-Ray field, as the UI shows it."""

    check: str
    status: Verdict
    reason: str


class Companion(BaseModel):
    """The same field read from the other document (RHP ``[●]`` beside the Prospectus value)."""

    doc: DocType
    page: int
    value: Value | None = None
    bbox: BBox | None = None  # where the companion value sits, so "show on page" can draw the box


class ApiCandidate(BaseModel):
    """One extractor's value for a field, as shown in the inspector."""

    extractor: str
    doc: DocType
    raw: str
    value: Value | None = None
    page: int
    score: float
    gold_match: bool | None = None  # only for IPOs that have gold labels


class SourceSentence(BaseModel):
    """The line of the page a value sits on; ``hit`` is the character span of the value in it."""

    text: str
    hit: tuple[int, int]


class XRayField(BaseModel):
    """One fact of the X-Ray with its source, verdict, checks and candidates."""

    field_id: str
    label_en: str
    label_hi: str
    type: str
    value: Value | None = None
    doc: DocType
    page: int
    printed_page: str | None = None
    bbox: BBox | None = None
    sentence: SourceSentence | None = None
    extractor: str
    score: float
    verdict: Verdict
    reason_code: ReasonCode
    reason: str
    companion: Companion | None = None
    checks: list[FieldCheck]
    candidates: list[ApiCandidate]


class BidClosedInfo(BaseModel):
    """ "Bid/offer closed on" as printed on the Prospectus cover (read by the extract stage)."""

    closed_on: date
    doc: DocType = "prospectus"
    page: int


class XRayResponse(BaseModel):
    """``GET /api/ipos/{id}/xray``: all fields and derived numbers."""

    ipo_id: str
    company: str
    built_at: datetime
    fields: list[XRayField]
    derived: dict[str, str]  # decimal strings, e.g. {"fresh_share_pct": "64.00"}
    bid_closed: BidClosedInfo | None = None  # absent in X-Rays built before run 2


# ------------------------------------------------------------------------- pages
class PageWord(BaseModel):
    """A word on a page: text ``t`` and box ``b``."""

    t: str
    b: BBox


class PageWords(BaseModel):
    """Every word on one page, for highlighting and text selection."""

    page: int
    width: float
    height: float
    words: list[PageWord]


# ------------------------------------------------------------------------- chat, voice
class SuggestedQuestion(BaseModel):
    """A question chip under the chat box (normal, trick or advice)."""

    text: str
    language: Language
    kind: Literal["normal", "trick", "advice"]


class ChatRequest(BaseModel):
    """``POST /api/chat`` body: the IPO, the question and its language."""

    ipo_id: str
    question: str
    language: Language = "en"
    source: Literal["typed", "voice", "chip"] = "typed"
    demo: bool = False


class VoiceResponse(BaseModel):
    """``POST /api/voice``: the transcript and the ASR model used."""

    transcript: str
    language: str
    asr_model: str
    ms: int


class GlossaryEntry(BaseModel):
    """A glossary term with its short definition."""

    term: str
    title: str
    body: str


# Lab payloads are read straight from eval_results/*.json; their shapes are pinned by the
# experiment result schema (05_DATA_AND_EVALUATION.md section 5.1) and typed in F7.
LabPayload = dict[str, Any]
