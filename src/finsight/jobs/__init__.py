"""Jobs: the stage runner, B06 events, the simplification queue, upload quotas and retention."""

from __future__ import annotations

from finsight.core.config import Settings
from finsight.db import Database
from finsight.jobs.costs import estimate as estimate_cost
from finsight.jobs.costs import summarise as summarise_costs
from finsight.jobs.launcher import (
    CloudRunLauncher,
    InlineLauncher,
    Launcher,
    LaunchError,
    cloud_run_launcher,
)
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
from finsight.jobs.simplify_worker import SIMPLIFIED, auto_enqueue, load_simplified, run_queue
from finsight.reports import write_report
from finsight.storage import Storage


def process_document(
    db: Database, storage: Storage, settings: Settings, doc_id: str, job_id: str
) -> JobResult:
    """Run the upload pipeline for one document (the worker's entry point)."""
    ctx = JobContext(doc_id=doc_id, job_id=job_id, db=db, storage=storage, settings=settings)
    result = run_job(ctx, upload_stages())
    doc = db.get_doc(doc_id)
    if doc is not None and result.rejection is None:
        write_report(storage, doc, doc.companion_of)
    return result


__all__ = [
    "IST",
    "READY_PARTS",
    "SIMPLIFIED",
    "SOURCE",
    "CloudRunLauncher",
    "InlineLauncher",
    "JobContext",
    "JobResult",
    "LaunchError",
    "Launcher",
    "Stage",
    "StageRejected",
    "UploadBlocked",
    "auto_enqueue",
    "check_upload_allowed",
    "cloud_run_launcher",
    "day_window",
    "estimate_cost",
    "load_simplified",
    "process_document",
    "run_job",
    "run_queue",
    "summarise_costs",
    "sweep",
    "upload_stages",
]
