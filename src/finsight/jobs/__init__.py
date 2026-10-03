"""Jobs: the stage runner, B06 events, the simplification queue, upload quotas and retention."""

from __future__ import annotations

from finsight.core.config import Settings
from finsight.db import Database
from finsight.jobs.launcher import CloudRunLauncher, InlineLauncher, Launcher
from finsight.jobs.pipeline import SOURCE, upload_stages
from finsight.jobs.quotas import IST, UploadBlocked, check_upload_allowed, day_window
from finsight.jobs.retention import sweep
from finsight.jobs.runner import (
    READY_PARTS,
    JobContext,
    JobResult,
    Stage,
    StageRejected,
    run_job,
)
from finsight.storage import Storage


def process_document(
    db: Database, storage: Storage, settings: Settings, doc_id: str, job_id: str
) -> JobResult:
    """Run the upload pipeline for one document (the worker's entry point)."""
    ctx = JobContext(doc_id=doc_id, job_id=job_id, db=db, storage=storage, settings=settings)
    return run_job(ctx, upload_stages())


__all__ = [
    "IST",
    "READY_PARTS",
    "SOURCE",
    "CloudRunLauncher",
    "InlineLauncher",
    "JobContext",
    "JobResult",
    "Launcher",
    "Stage",
    "StageRejected",
    "UploadBlocked",
    "check_upload_allowed",
    "day_window",
    "process_document",
    "run_job",
    "sweep",
    "upload_stages",
]
