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
from finsight.api.uploads_state import CurrentUser, UState
from finsight.core.schemas import DocRecord, DocType
from finsight.reports import ReportOverview, assemble, etag

router = APIRouter(
    prefix="/api",
    responses={"4XX": {"model": ErrorResponse}, "5XX": {"model": ErrorResponse}},
)

DocId = Annotated[str, Path(min_length=1, max_length=40)]
MAX_STREAM_S = 30 * 60  # a job's timeout; the client reconnects with Last-Event-ID after this


class StageState(BaseModel):
    stage: str
    status: Literal["running", "done", "failed"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    detail: dict[str, object] | None = None


class DocDetail(BaseModel):
    doc: DocRecord
    job_id: str | None = None
    stages: list[StageState]
    companion_doc_id: str | None = None


class MyUpload(BaseModel):
    doc_id: str
    company: str | None
    doc_type: DocType | None
    created_at: datetime
    status: str


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


@router.get("/docs/{doc_id}", tags=["docs"])
def get_doc(doc_id: DocId, state: UState) -> DocDetail:
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
    return [
        MyUpload(
            doc_id=d.doc_id,
            company=d.company,
            doc_type=d.doc_type,
            created_at=d.created_at,
            status=d.status,
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
    report = assemble(state.storage, doc, doc.companion_of)
    tag = etag(report)
    response.headers["ETag"] = tag
    if doc.status == "ready":
        response.headers["Cache-Control"] = "public, max-age=3600"
    if if_none_match == tag:
        return Response(status_code=304, headers=dict(response.headers))  # type: ignore[return-value]
    return report
