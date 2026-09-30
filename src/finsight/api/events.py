"""One pydantic model per SSE event of ``POST /api/chat`` (06_API_CONTRACT.md).

Registered in the OpenAPI components (see ``app.py``) so the frontend gets generated
types for every event, which OpenAPI would not describe for a streaming response.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from finsight.core.schemas import Amount, BBox, DocType, ReasonCode, Verdict

StageName = Literal["guard", "retrieving", "generating", "verifying", "done"]


class StageEvent(BaseModel):
    name: StageName
    status: Literal["start", "end"]
    ms: int | None = None


class FactSummary(BaseModel):
    """A short X-Ray fact shown on the advice-refusal card."""

    field_id: str
    label_en: str
    label_hi: str
    display: str
    doc: DocType
    page: int


class GuardEvent(BaseModel):
    blocked: bool
    reason: str
    facts: list[FactSummary]


class RetrievedPassage(BaseModel):
    n: int
    id: str
    doc: DocType
    page_start: int
    page_end: int
    section: str
    snippet: str
    bm25_rank: int | None = None
    dense_rank: int | None = None
    fused_rank: int | None = None
    rerank_score: float | None = None


class RetrievalEvent(BaseModel):
    passages: list[RetrievedPassage]
    dropped: list[RetrievedPassage]


class AbstainEvent(BaseModel):
    reason: Literal["low_retrieval_score"]
    closest_passage: RetrievedPassage | None = None


class TokenEvent(BaseModel):
    text: str


class Citation(BaseModel):
    n: int
    char_start: int
    char_end: int


class AnswerEvent(BaseModel):
    text: str
    citations: list[Citation]


class Evidence(BaseModel):
    passage_id: str
    doc: DocType
    page: int
    char_span: tuple[int, int]
    bbox: BBox | None = None
    value: Amount | None = None


class VerdictEvent(BaseModel):
    index: int
    answer_char_span: tuple[int, int]
    answer_value: Amount
    status: Verdict
    reason_code: ReasonCode
    reason: str
    evidence: Evidence | None = None


class FinalEvent(BaseModel):
    trace_id: str
    score: float | None
    n_numbers: int
    # Keys equal the stage names: guard, retrieving, generating, verifying.
    timings_ms: dict[str, int]


class ErrorEvent(BaseModel):
    code: Literal["llm_unavailable", "models_warming_up", "internal_error"]
    message: str


# SSE ``event:`` name -> payload model, in the order events are emitted.
EVENT_MODELS: dict[str, type[BaseModel]] = {
    "stage": StageEvent,
    "guard": GuardEvent,
    "retrieval": RetrievalEvent,
    "abstain": AbstainEvent,
    "token": TokenEvent,
    "answer": AnswerEvent,
    "verdict": VerdictEvent,
    "final": FinalEvent,
    "error": ErrorEvent,
}
