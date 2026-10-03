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
    """A chat pipeline stage starting or ending, with its time in ms."""

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
    """The guard's decision; when blocked, the facts shown instead of advice."""

    blocked: bool
    reason: str
    facts: list[FactSummary]


class RetrievedPassage(BaseModel):
    """One passage the retriever returned, with its rank in each method."""

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
    """The passages kept for the prompt and the ones dropped."""

    passages: list[RetrievedPassage]
    dropped: list[RetrievedPassage]


class AbstainEvent(BaseModel):
    """FinSight declines to answer because retrieval found nothing close enough."""

    reason: Literal["low_retrieval_score"]
    closest_passage: RetrievedPassage | None = None


class TokenEvent(BaseModel):
    """A piece of streamed answer text."""

    text: str


class Citation(BaseModel):
    """A ``[n]`` citation in the answer and its character span."""

    n: int
    char_start: int
    char_end: int


class AnswerEvent(BaseModel):
    """The full answer text with its citations, sent once streaming ends."""

    text: str
    citations: list[Citation]


class Evidence(BaseModel):
    """Where a checked number was found: passage, page, span and box."""

    passage_id: str
    doc: DocType
    page: int
    char_span: tuple[int, int]
    bbox: BBox | None = None
    value: Amount | None = None


class VerdictEvent(BaseModel):
    """The verifier's mark for one number in the answer."""

    index: int
    answer_char_span: tuple[int, int]
    answer_value: Amount
    status: Verdict
    reason_code: ReasonCode
    reason: str
    evidence: Evidence | None = None


class FinalEvent(BaseModel):
    """The last chat event: trace id, score, number count and stage timings."""

    trace_id: str
    score: float | None
    n_numbers: int
    # Keys equal the stage names: guard, retrieving, generating, verifying.
    timings_ms: dict[str, int]


class ErrorEvent(BaseModel):
    """A chat error the UI can show (model unavailable, warming up, internal)."""

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


# ------------------------------------------------------------------ document job events (B06 §2)
class JobStageEvent(BaseModel):
    """A document job stage starting, ending or failing (B06 §2)."""

    stage: str
    status: Literal["start", "end", "failed"]
    detail: dict[str, object] | None = None


class JobProgressEvent(BaseModel):
    """Progress inside a long stage: ``done`` of ``total`` items."""

    stage: str
    done: int
    total: int


class JobReadyEvent(BaseModel):
    """A report part is ready and the UI can fetch it."""

    part: Literal["facts", "redflags", "risk_level", "risks", "compare", "chat"]


class RiskSimplifiedEvent(BaseModel):
    """A risk's plain-English rewrite finished (or was rejected or failed)."""

    rid: str
    simple_status: Literal["pending", "ready", "rejected", "failed"]


class JobDoneEvent(BaseModel):
    """The job finished: ready, partial (some stages failed) or failed."""

    status: Literal["ready", "partial", "failed"]
    failed_stages: list[str]


# SSE ``event:`` name -> payload model for ``GET /api/docs/{doc_id}/events``.
JOB_EVENT_MODELS: dict[str, type[BaseModel]] = {
    "stage": JobStageEvent,
    "progress": JobProgressEvent,
    "ready": JobReadyEvent,
    "risk_simplified": RiskSimplifiedEvent,
    "done": JobDoneEvent,
}
