"""Admin endpoints (B06 §6): failed jobs, for the admin email allow-list only.

``auth.admin_emails`` lists who may call them; everyone else gets 403 ``forbidden``. With
``auth.mode: off`` (laptop) the single local user is the admin.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from finsight.api.errors import ApiError, ErrorResponse
from finsight.api.uploads_state import CurrentUser, UState
from finsight.auth import User
from finsight.core.schemas import Job
from finsight.db import utcnow

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={"4XX": {"model": ErrorResponse}, "5XX": {"model": ErrorResponse}},
)


def admin_user(user: CurrentUser) -> User:
    """The caller, if on the admin allow-list (403 ``forbidden`` otherwise)."""
    if not user.is_admin:
        raise ApiError(403, "forbidden", "This page is only for the FinSight admin.")
    return user


Admin = Annotated[User, Depends(admin_user)]


class FailedJob(BaseModel):
    """One row of ``GET /api/admin/jobs``."""

    job: Job
    created_at: datetime
    company: str | None = None


@router.get("/jobs")
def admin_jobs(
    state: UState,
    _admin: Admin,
    status: Literal["failed", "done", "running", "queued"] = "failed",
    days: Annotated[int, Query(ge=1, le=92)] = 31,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[FailedJob]:
    """Recent jobs with this status (failed by default), newest first."""
    rows = state.db.jobs_since(utcnow() - timedelta(days=days), status=status, limit=limit)
    out = []
    for job, created_at in rows:
        doc = state.db.get_doc(job.doc_id)
        out.append(FailedJob(job=job, created_at=created_at, company=doc.company if doc else None))
    return out
