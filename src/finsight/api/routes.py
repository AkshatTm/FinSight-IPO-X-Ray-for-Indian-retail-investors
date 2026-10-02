"""Every endpoint of 06_API_CONTRACT.md (ADR-024: contract first, filled in at P4.1).

The signatures, parameters and response models here *are* the contract: the OpenAPI
document generated from them feeds the frontend's TypeScript types.
"""

from __future__ import annotations

import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response, StreamingResponse

from finsight.api import content
from finsight.api.demo import Event
from finsight.api.errors import ApiError, ErrorResponse
from finsight.api.events import ErrorEvent
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
from finsight.api.state import AppState, get_state
from finsight.core.schemas import DocType, Language, Trace

router = APIRouter(
    prefix="/api",
    responses={"4XX": {"model": ErrorResponse}, "5XX": {"model": ErrorResponse}},
)

Doc = Annotated[DocType, Query(description="Which document: the RHP or the final Prospectus.")]
State = Annotated[AppState, Depends(get_state)]
MAX_QUESTION = 300
MAX_AUDIO_BYTES = 4_000_000
MAX_AUDIO_S = 20.5  # the client stops at 20 s; the half second absorbs encoder padding


@router.get("/health", tags=["system"])
def health(state: State) -> HealthResponse:
    return state.models.health()


@router.get("/ipos", tags=["ipos"])
def list_ipos(
    state: State,
    q: Annotated[str | None, Query(description="Company or sector search.")] = None,
    sector: str | None = None,
    year: int | None = None,
    sort: Literal["listing_date", "issue_size"] = "listing_date",
) -> list[IpoSummary]:
    return state.store.list_ipos(q, sector, year, sort)


@router.get("/ipos/{id}", tags=["ipos"])
def get_ipo(id: str, state: State) -> IpoDetail:
    return state.store.detail(id)


@router.get("/ipos/{id}/xray", tags=["ipos"])
def get_xray(id: str, state: State) -> XRayResponse:
    return state.store.xray(id)


@router.get(
    "/ipos/{id}/pages/{n}",
    tags=["ipos"],
    response_class=Response,
    responses={
        200: {"content": {"image/webp": {"schema": {"type": "string", "format": "binary"}}}}
    },
)
def get_page_image(id: str, n: int, state: State, doc: Doc = "rhp") -> Response:
    path = state.store.page_path(id, n, doc)
    return Response(
        path.read_bytes(),
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/ipos/{id}/pages/{n}/words", tags=["ipos"])
def get_page_words(id: str, n: int, state: State, doc: Doc = "rhp") -> PageWords:
    return state.store.words(id, n, doc)


@router.get("/ipos/{id}/suggested-questions", tags=["ipos"])
def suggested_questions(id: str, state: State) -> list[SuggestedQuestion]:
    return state.store.suggested(id)


def sse(events: Iterator[Event]) -> Iterator[str]:
    """Server-sent events: ``event:`` name, JSON ``data:``, blank line."""
    for name, event in events:
        yield f"event: {name}\ndata: {event.model_dump_json(exclude_none=True)}\n\n"


def _error_stream(code: Literal["internal_error"], message: str) -> Iterator[Event]:
    yield "error", ErrorEvent(code=code, message=message)


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
def chat(body: ChatRequest, state: State) -> Response:
    state.store.get(body.ipo_id)  # unknown ids are a normal 404, not a stream
    question = body.question.strip()
    if not question or len(question) > MAX_QUESTION:
        raise ApiError(
            422, "validation_error", f"The question must be 1 to {MAX_QUESTION} characters."
        )
    recorded = state.demo.has(body.ipo_id, question, body.language)
    if recorded and (body.demo or state.settings.demo_mode):
        events = state.demo.replay(body.ipo_id, question, body.language)
    elif body.demo:
        events = _error_stream("internal_error", "No recorded answer for this question.")
    else:
        events = state.chat().events(body.ipo_id, question, body.language)
    return StreamingResponse(
        sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/voice", tags=["chat"])
def voice(
    state: State,
    audio: Annotated[UploadFile, File(description="webm/opus or wav, at most 20 s.")],
    language: Annotated[str, Form()] = "hi",
) -> VoiceResponse:
    asr = state.asr()
    if asr is None:
        raise ApiError(
            503,
            "asr_failed",
            "Voice input is switched off in this profile.",
            hint="Type the question instead.",
        )
    data = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise ApiError(422, "asr_failed", "The audio file is empty.")
    if len(data) > MAX_AUDIO_BYTES:
        raise ApiError(
            413, "audio_too_long", "That recording is too long.", hint="Keep it under 20 seconds."
        )
    suffix = Path(audio.filename or "").suffix or ".webm"
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"question{suffix}"
        path.write_bytes(data)
        try:
            result = asr.transcribe(path, language)
        except Exception as exc:  # decoder and model errors: one friendly code, details in the log
            raise ApiError(
                422,
                "asr_failed",
                "Could not understand the audio.",
                hint="Try again in a quieter place, or type the question.",
            ) from exc
    if result.duration_s > MAX_AUDIO_S:
        raise ApiError(413, "audio_too_long", "That recording is longer than 20 seconds.")
    return VoiceResponse(
        transcript=result.text,
        language=result.language,
        asr_model=result.model,
        ms=int((time.perf_counter() - started) * 1000),
    )


@router.get("/traces/{trace_id}", tags=["chat"])
def get_trace(trace_id: str, state: State) -> Trace:
    trace = state.traces.get(trace_id)
    if trace is None:
        raise ApiError(404, "not_available", f"No trace '{trace_id}'.")
    return trace


@router.get("/lab/ladder", tags=["lab"])
def lab_ladder(state: State) -> LabPayload:
    return content.lab(state.settings.paths.eval_dir, "ladder")


@router.get("/lab/fields", tags=["lab"])
def lab_fields(state: State) -> LabPayload:
    return content.lab(state.settings.paths.eval_dir, "fields")


@router.get("/lab/verifier", tags=["lab"])
def lab_verifier(state: State) -> LabPayload:
    return content.lab(state.settings.paths.eval_dir, "verifier")


@router.get("/lab/weaklabels", tags=["lab"])
def lab_weaklabels(state: State) -> LabPayload:
    return content.lab(state.settings.paths.eval_dir, "weaklabels")


@router.get("/lab/frontier", tags=["lab"])
def lab_frontier(state: State) -> LabPayload:
    return content.lab(state.settings.paths.eval_dir, "frontier")


@router.get("/lab/retrieval", tags=["lab"])
def lab_retrieval(state: State) -> LabPayload:
    return content.lab(state.settings.paths.eval_dir, "retrieval")


@router.get("/lab/asr", tags=["lab"])
def lab_asr(state: State) -> LabPayload:
    return content.lab(state.settings.paths.eval_dir, "asr")


@router.get("/glossary", tags=["content"])
def glossary(lang: Language = "en") -> list[GlossaryEntry]:
    return content.glossary(lang)
