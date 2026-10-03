"""Upload endpoints (B06 §2): init → PUT to storage (or POST here locally) → complete.

The server recomputes the SHA-256 on ``complete``, so the dedupe cannot be poisoned. The PDF
itself is validated by the worker job, never in the API process (B02 §11); validation
rejections arrive as the ``validated`` stage failure and as ``doc.rejection``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Request
from pydantic import BaseModel, Field

from finsight.api.errors import ApiError, ErrorResponse
from finsight.api.uploads_state import CurrentUser, UState
from finsight.core.ids import make_doc_id
from finsight.core.schemas import DocRecord
from finsight.db import utcnow
from finsight.jobs import SOURCE, LaunchError, UploadBlocked, check_upload_allowed
from finsight.storage import doc_key

router = APIRouter(
    prefix="/api/uploads",
    tags=["uploads"],
    responses={"4XX": {"model": ErrorResponse}, "5XX": {"model": ErrorResponse}},
)

DocId = Annotated[str, Path(pattern=r"^doc_[0-9a-f]{16}$")]
_BLOCKED_STATUS = {"uploads_disabled": 503, "quota_exceeded": 429, "global_quota_exceeded": 429}
_BLOCKED_TEXT = {
    "uploads_disabled": "Uploads are paused right now.",
    "quota_exceeded": "You've reached today's upload limit.",
    "global_quota_exceeded": "FinSight has reached today's upload limit for everyone.",
}


class UploadInit(BaseModel):
    filename: str = Field(max_length=300)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class UploadInitResponse(BaseModel):
    status: Literal["exists", "upload"]
    doc_id: str
    upload_url: str | None = None
    upload_method: Literal["PUT", "POST"] | None = None
    expires_at: datetime | None = None


class UploadComplete(BaseModel):
    doc_id: str
    job_id: str
    status: Literal["queued"]


class UploadLimits(BaseModel):
    """What the upload page shows before anyone uploads (B05 §3)."""

    enabled: bool
    max_mb: int
    max_pages: int
    per_user_per_day: int


@router.get("/limits")
def upload_limits(state: UState) -> UploadLimits:
    cfg = state.settings.uploads
    return UploadLimits(
        enabled=cfg.enabled,
        max_mb=cfg.max_mb,
        max_pages=cfg.max_pages,
        per_user_per_day=cfg.per_user_per_day,
    )


def _too_large(state: UState, size: int) -> None:
    limit = state.settings.uploads.max_mb
    if size > limit * 1024 * 1024:
        raise ApiError(422, "too_large", f"This file is larger than {limit} MB.")


@router.post("/init")
def init_upload(body: UploadInit, state: UState, user: CurrentUser) -> UploadInitResponse:
    """Start an upload, or point to the existing report when the file was already analysed."""
    sha = body.sha256.lower()
    doc_id = make_doc_id(sha)
    existing = state.db.get_doc(doc_id)
    if existing is not None and existing.status != "uploading":
        return UploadInitResponse(status="exists", doc_id=doc_id)
    _too_large(state, body.size_bytes)
    try:
        check_upload_allowed(state.db, state.settings.uploads, user.id)
    except UploadBlocked as err:
        raise ApiError(
            _BLOCKED_STATUS[err.code],
            err.code,  # type: ignore[arg-type]
            _BLOCKED_TEXT[err.code],
            limit=err.limit or None,
            resets_at=err.resets_at,
        ) from err
    if existing is None:
        state.db.insert_doc(
            DocRecord(
                doc_id=doc_id,
                sha256=sha,
                uploaded_by=user.id,
                created_at=utcnow(),
                status="uploading",
            )
        )
    else:
        state.db.update_doc(doc_id, uploaded_by=user.id)
    state.db.record_upload(user.id, doc_id)
    signed = state.storage.signed_upload_url(
        doc_key(doc_id, SOURCE), "application/pdf", state.settings.storage.signed_url_ttl_s
    )
    return UploadInitResponse(
        status="upload",
        doc_id=doc_id,
        upload_url=signed.url,
        upload_method="PUT" if signed.method == "PUT" else "POST",
        expires_at=signed.expires_at,
    )


def _pending(state: UState, doc_id: str, user_id: str) -> DocRecord:
    doc = state.db.get_doc(doc_id)
    if doc is None or doc.status != "uploading" or doc.uploaded_by != user_id:
        raise ApiError(
            409, "upload_not_started", "Start the upload first.", hint="POST /api/uploads/init"
        )
    return doc


@router.post(
    "/{doc_id}/file",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def upload_file(
    doc_id: DocId, request: Request, state: UState, user: CurrentUser
) -> dict[str, str]:
    """Local profiles only: the raw PDF bytes (the cloud profiles PUT to a signed GCS URL)."""
    _pending(state, doc_id, user.id)
    limit = state.settings.uploads.max_mb * 1024 * 1024
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        _too_large(state, int(declared))
    data = await request.body()
    _too_large(state, len(data))
    state.storage.put_bytes(doc_key(doc_id, SOURCE), data, "application/pdf")
    return {"doc_id": doc_id, "status": "stored"}


@router.post("/{doc_id}/complete")
def complete_upload(doc_id: DocId, state: UState, user: CurrentUser) -> UploadComplete:
    """Check the stored file's SHA-256 and size, then queue the processing job."""
    doc = _pending(state, doc_id, user.id)
    key = doc_key(doc_id, SOURCE)
    if not state.storage.exists(key):
        raise ApiError(409, "upload_not_started", "The file has not arrived yet. Please try again.")
    data = state.storage.get_bytes(key)
    if hashlib.sha256(data).hexdigest() != doc.sha256:
        state.storage.delete_prefix(f"docs/{doc_id}/")
        raise ApiError(
            422, "hash_mismatch", "The upload didn't finish correctly. Please try again."
        )
    try:
        _too_large(state, len(data))
    except ApiError:
        state.storage.delete_prefix(f"docs/{doc_id}/")
        raise
    state.db.update_doc(doc_id, status="processing")
    job = state.db.create_job(doc_id)
    state.db.append_event(job.job_id, "stage", {"stage": "received", "status": "end"})
    try:
        state.launcher.launch(doc_id, job.job_id)
    except LaunchError as err:
        # The file is stored and the job recorded: an operator can start it again by hand
        # (docs/runbooks/DEPLOY_RUNBOOK.md); the reader sees a failed job, not a hang.
        state.db.update_job(
            job.job_id, status="failed", finished_at=utcnow(), error=f"launch: {err}"[:500]
        )
        state.db.update_doc(doc_id, status="failed")
        state.db.append_event(job.job_id, "done", {"status": "failed", "failed_stages": []})
        raise ApiError(
            503, "worker_unavailable", "We couldn't start processing. Please try again later."
        ) from err
    return UploadComplete(doc_id=doc_id, job_id=job.job_id, status="queued")
