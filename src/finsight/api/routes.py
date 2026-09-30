"""Every endpoint of 06_API_CONTRACT.md, answering 501 until its sub-phase lands (ADR-024).

The signatures, parameters and response models here *are* the contract: the OpenAPI
document generated from them feeds the frontend's TypeScript types from day one.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import Response

from finsight.api.errors import ErrorResponse, not_implemented
from finsight.api.models import (
    ChatRequest,
    GlossaryEntry,
    HealthResponse,
    IpoDetail,
    IpoSummary,
    LabPayload,
    PageWords,
    SuggestedQuestion,
    VoiceResponse,
    XRayResponse,
)
from finsight.core.schemas import DocType, Language, Trace

router = APIRouter(
    prefix="/api",
    responses={"4XX": {"model": ErrorResponse}, "5XX": {"model": ErrorResponse}},
)

Doc = Annotated[DocType, Query(description="Which document: the RHP or the final Prospectus.")]


@router.get("/health", tags=["system"])
def health() -> HealthResponse:
    raise not_implemented("Health")


@router.get("/ipos", tags=["ipos"])
def list_ipos(
    q: Annotated[str | None, Query(description="Company or sector search.")] = None,
    sector: str | None = None,
    year: int | None = None,
    sort: Literal["listing_date", "issue_size"] = "listing_date",
) -> list[IpoSummary]:
    raise not_implemented("IPO list")


@router.get("/ipos/{id}", tags=["ipos"])
def get_ipo(id: str) -> IpoDetail:
    raise not_implemented("IPO detail")


@router.get("/ipos/{id}/xray", tags=["ipos"])
def get_xray(id: str) -> XRayResponse:
    raise not_implemented("X-Ray")


@router.get(
    "/ipos/{id}/pages/{n}",
    tags=["ipos"],
    response_class=Response,
    responses={
        200: {"content": {"image/webp": {"schema": {"type": "string", "format": "binary"}}}}
    },
)
def get_page_image(id: str, n: int, doc: Doc = "rhp") -> Response:
    raise not_implemented("Page image")


@router.get("/ipos/{id}/pages/{n}/words", tags=["ipos"])
def get_page_words(id: str, n: int, doc: Doc = "rhp") -> PageWords:
    raise not_implemented("Page words")


@router.get("/ipos/{id}/suggested-questions", tags=["ipos"])
def suggested_questions(id: str) -> list[SuggestedQuestion]:
    raise not_implemented("Suggested questions")


@router.post(
    "/chat",
    tags=["chat"],
    response_class=Response,
    responses={
        200: {
            "description": "Server-sent events; see the x-sse-events map for each payload model.",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
def chat(body: ChatRequest) -> Response:
    raise not_implemented("Chat")


@router.post("/voice", tags=["chat"])
def voice(
    audio: Annotated[UploadFile, File(description="webm/opus or wav, at most 20 s.")],
    language: Annotated[str, Form()] = "hi",
) -> VoiceResponse:
    raise not_implemented("Voice")


@router.get("/traces/{trace_id}", tags=["chat"])
def get_trace(trace_id: str) -> Trace:
    raise not_implemented("Trace")


@router.get("/lab/ladder", tags=["lab"])
def lab_ladder() -> LabPayload:
    raise not_implemented("Lab ladder")


@router.get("/lab/fields", tags=["lab"])
def lab_fields() -> LabPayload:
    raise not_implemented("Lab fields")


@router.get("/lab/verifier", tags=["lab"])
def lab_verifier() -> LabPayload:
    raise not_implemented("Lab verifier")


@router.get("/lab/weaklabels", tags=["lab"])
def lab_weaklabels() -> LabPayload:
    raise not_implemented("Lab weak labels")


@router.get("/lab/frontier", tags=["lab"])
def lab_frontier() -> LabPayload:
    raise not_implemented("Lab frontier comparison")


@router.get("/glossary", tags=["content"])
def glossary(lang: Language = "en") -> list[GlossaryEntry]:
    raise not_implemented("Glossary")
