"""Document endpoints (B06 §2-3): status, live events with replay, my uploads, the report."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Path, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from finsight.api.errors import ApiError, ErrorResponse
from finsight.api.ipos import clear_loader_caches
from finsight.api.uploads_state import CurrentUser, UState
from finsight.auth import User
from finsight.core.schemas import DocRecord, DocType
from finsight.db import utcnow
from finsight.jobs import (
    LaunchError,
    delete_document,
    models_fingerprint,
    reset_for_reanalysis,
    run_preflight,
)
from finsight.jobs.cache import CacheState, cache_state
from finsight.reports import ReportOverview, assemble, etag

router = APIRouter(
    prefix="/api",
    responses={"4XX": {"model": ErrorResponse}, "5XX": {"model": ErrorResponse}},
)

DocId = Annotated[str, Path(min_length=1, max_length=40)]
MAX_STREAM_S = 30 * 60  # a job's timeout; the client reconnects with Last-Event-ID after this


class StageState(BaseModel):
    """One pipeline stage of an uploaded document, rebuilt from its events."""

    stage: str
    status: Literal["running", "done", "failed"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    detail: dict[str, object] | None = None


class CacheInfo(BaseModel):
    """Is the stored analysis current (CC-04)? ``reanalysing`` is true when opening a stale
    analysis just started a re-run; ``blocked`` says why a stale one was kept as it is."""

    state: CacheState
    analysis_status: Literal["complete", "degraded", "failed"] | None = None
    degraded_reasons: list[str] = []
    reanalysing: bool = False
    blocked: str | None = None


class ReanalyseBody(BaseModel):
    """``POST /api/docs/{doc_id}/reanalyse``: which missing models to analyse without."""

    analyse_without: list[Literal["ollama", "classifier", "embeddings", "reranker"]] = []


class JobStarted(BaseModel):
    """A re-analysis that was queued."""

    doc_id: str
    job_id: str
    status: Literal["queued"]


class DocDetail(BaseModel):
    """``GET /api/docs/{doc_id}``: the document, its latest job and stages."""

    doc: DocRecord
    job_id: str | None = None
    stages: list[StageState]
    companion_doc_id: str | None = None
    cache: CacheInfo | None = None


class MyUpload(BaseModel):
    """One row of ``/api/me/uploads``."""

    doc_id: str
    company: str | None
    doc_type: DocType | None
    created_at: datetime
    status: str
    analysis_status: Literal["complete", "degraded", "failed"] | None = None


def _doc(state: UState, doc_id: str) -> DocRecord:
    doc = state.db.get_doc(doc_id)
    if doc is None or doc.status == "uploading":
        raise ApiError(
            404,
            "doc_not_found",
            "We couldn't find this report.",
            hint="It may have expired after 30 days.",
        )
    return doc


def _start(state: UState, doc_id: str, skip: list[str]) -> str:
    """Clear the old analysis (keeping the PDF) and launch a new job for it."""
    job_id = reset_for_reanalysis(state.db, state.storage, state.settings, doc_id, skip)
    try:
        state.launcher.launch(doc_id, job_id)
    except LaunchError as err:
        state.db.update_job(
            job_id, status="failed", finished_at=utcnow(), error=f"launch: {err}"[:500]
        )
        state.db.update_doc(doc_id, status="failed")
        state.db.append_event(job_id, "done", {"status": "failed", "failed_stages": []})
        raise ApiError(
            503, "worker_unavailable", "We couldn't start processing. Please try again later."
        ) from err
    return job_id


def _cache_info(state: UState, doc: DocRecord) -> CacheInfo:
    """The cache state of a finished analysis. A stale one is re-run at once when the models
    are there (preflight passes) and kept, with a ``blocked`` note, when they are not."""
    if doc.status not in ("ready", "partial"):
        return CacheInfo(
            state="fresh",
            analysis_status=doc.analysis_status,
            degraded_reasons=doc.degraded_reasons,
        )
    fingerprint = models_fingerprint(state.settings, skip=doc.skipped_models)
    current = cache_state(doc, state.settings, fingerprint)
    info = CacheInfo(
        state=current, analysis_status=doc.analysis_status, degraded_reasons=doc.degraded_reasons
    )
    if current == "fresh" or doc.is_showcase:
        return info
    pre = run_preflight(state.settings)
    if not pre.ok:
        info.blocked = pre.message()
        return info
    _start(state, doc.doc_id, [])
    info.reanalysing = True
    return info


def _owned(doc: DocRecord, user: User) -> None:
    if doc.is_showcase:
        raise ApiError(403, "forbidden", "The showcase IPOs can't be deleted or re-analysed here.")
    if doc.uploaded_by != user.id and not user.is_admin:
        raise ApiError(403, "forbidden", "Only the person who uploaded this can change it.")


def _idle(doc: DocRecord) -> None:
    if doc.status == "processing":
        raise ApiError(
            409, "doc_busy", "This report is still being made.", hint="Try again when it finishes."
        )


@router.delete("/docs/{doc_id}", tags=["docs"])
def delete_doc(doc_id: DocId, state: UState, user: CurrentUser) -> dict[str, str]:
    """Delete the analysis completely: stored files, indexes, page images, jobs and rows.
    Uploading the same PDF again then analyses it from scratch."""
    doc = _doc(state, doc_id)
    _owned(doc, user)
    _idle(doc)
    delete_document(state.db, state.storage, state.settings, doc_id)
    clear_loader_caches()
    return {"deleted": doc_id}


@router.post("/docs/{doc_id}/reanalyse", tags=["docs"])
def reanalyse_doc(
    doc_id: DocId, state: UState, user: CurrentUser, body: ReanalyseBody | None = None
) -> JobStarted:
    """Force a new analysis of the stored PDF. A missing model refuses it (503
    ``models_unavailable``) unless it is listed in ``analyse_without``."""
    doc = _doc(state, doc_id)
    _owned(doc, user)
    _idle(doc)
    skip = list(body.analyse_without) if body else []
    pre = run_preflight(state.settings, skip)
    if not pre.ok:
        raise ApiError(
            503,
            "models_unavailable",
            pre.message(),
            hint="Start the missing model, or analyse without it.",
        )
    job_id = _start(state, doc_id, skip)
    clear_loader_caches()
    return JobStarted(doc_id=doc_id, job_id=job_id, status="queued")


@router.get("/docs/{doc_id}", tags=["docs"])
def get_doc(doc_id: DocId, state: UState) -> DocDetail:
    """An uploaded document with the state of each stage of its latest job."""
    doc = _doc(state, doc_id)
    cache = _cache_info(state, doc)
    if cache.reanalysing:
        doc = _doc(state, doc_id)
    job = state.db.latest_job(doc_id)
    stages: dict[str, StageState] = {}
    if job is not None:
        for event in state.db.events_after(job.job_id):
            if event.event != "stage":
                continue
            name = str(event.data["stage"])
            status = event.data["status"]
            current = stages.get(name) or StageState(stage=name, status="running")
            if status == "start":
                current.started_at = event.ts
            else:
                current.status = "done" if status == "end" else "failed"
                current.finished_at = event.ts
                detail = event.data.get("detail")
                current.detail = detail if isinstance(detail, dict) else None
            stages[name] = current
    return DocDetail(
        doc=doc,
        job_id=job.job_id if job else None,
        stages=list(stages.values()),
        companion_doc_id=doc.companion_of,
        cache=cache,
    )


@router.get(
    "/docs/{doc_id}/events",
    tags=["docs"],
    response_class=Response,
    responses={
        200: {
            "description": "Server-sent events; see the x-sse-events map for each payload model.",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
def doc_events(
    doc_id: DocId,
    state: UState,
    request: Request,
    last_event_id: Annotated[str | None, Header()] = None,
) -> Response:
    """Stage events of the latest job; ``Last-Event-ID`` replays everything after that ``seq``.

    The Supabase pooler has no LISTEN/NOTIFY, so the stream polls ``job_events`` about once a
    second (``jobs.poll_interval_s``) and ends after the ``done`` event.
    """
    _doc(state, doc_id)
    job = state.db.latest_job(doc_id)
    if job is None:
        raise ApiError(404, "doc_not_found", "This document has no processing job yet.")
    after = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
    interval = state.settings.jobs.poll_interval_s

    async def stream() -> AsyncIterator[str]:
        """Poll the event table and send new events until ``done`` or disconnect."""
        nonlocal after
        waited = 0.0
        while waited < MAX_STREAM_S:
            for event in state.db.events_after(job.job_id, after):
                after = event.seq
                yield f"id: {event.seq}\nevent: {event.event}\ndata: {json.dumps(event.data)}\n\n"
                if event.event == "done":
                    return
            if await request.is_disconnected():
                return
            await asyncio.sleep(interval)
            waited += interval

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/me/uploads", tags=["docs"])
def my_uploads(state: UState, user: CurrentUser) -> list[MyUpload]:
    """The signed-in user's uploads, newest first."""
    return [
        MyUpload(
            doc_id=d.doc_id,
            company=d.company,
            doc_type=d.doc_type,
            created_at=d.created_at,
            status=d.status,
            analysis_status=d.analysis_status,
        )
        for d in state.db.docs_by_user(user.id)
        if d.status != "uploading"
    ]


@router.get("/docs/{doc_id}/report", tags=["docs"])
def get_report(
    doc_id: DocId,
    state: UState,
    response: Response,
    if_none_match: Annotated[str | None, Header()] = None,
) -> ReportOverview:
    """The assembled overview; ready reports are cacheable for an hour (B06 §3)."""
    doc = _doc(state, doc_id)
    if _cache_info(state, doc).reanalysing:
        doc = _doc(state, doc_id)
    report = assemble(state.storage, doc, doc.companion_of)
    tag = etag(report)
    response.headers["ETag"] = tag
    if doc.status == "ready" and doc.analysis_status == "complete":  # degraded: never cached
        response.headers["Cache-Control"] = "public, max-age=3600"
    if if_none_match == tag:
        return Response(status_code=304, headers=dict(response.headers))  # type: ignore[return-value]
    return report
