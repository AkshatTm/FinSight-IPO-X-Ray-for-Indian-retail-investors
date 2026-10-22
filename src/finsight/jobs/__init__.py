"""Jobs: the stage runner, B06 events, the simplification queue, upload quotas and retention."""

from __future__ import annotations

from finsight.core.config import Settings
from finsight.db import Database, utcnow
from finsight.jobs.cache import (
    analysis_status,
    cache_key,
    delete_document,
    models_fingerprint,
    reset_for_reanalysis,
)
from finsight.jobs.launcher import (
    InlineLauncher,
    Launcher,
    LaunchError,
)
from finsight.jobs.pipeline import SOURCE, upload_stages
from finsight.jobs.preflight import STAGES_NEEDING, PreflightResult, run_preflight
from finsight.jobs.quotas import IST, UploadBlocked, check_upload_allowed, day_window
from finsight.jobs.retention import sweep
from finsight.jobs.runner import (
    READY_PARTS,
    JobContext,
    JobResult,
    Stage,
    StageRejected,
    StageTimeout,
    run_job,
)
from finsight.jobs.simplify_worker import (
    SIMPLIFIED,
    SimplifyDrain,
    auto_enqueue,
    load_simplified,
    run_queue,
)
from finsight.reports import write_report
from finsight.storage import Storage


def _refuse(ctx: JobContext, result: PreflightResult) -> JobResult:
    """End a job that never started because a model is missing (CC-04): a clear message, no
    partial report."""
    reasons = [f"model_missing:{c.model}" for c in result.blocking]
    ctx.db.update_job(
        ctx.job_id, stage="preflight", status="failed", finished_at=utcnow(),
        error=result.message()[:500],
    )  # fmt: skip
    ctx.db.update_doc(
        ctx.doc_id, status="failed", analysis_status="failed", degraded_reasons=reasons
    )
    ctx.emit(
        "stage",
        {
            "stage": "preflight",
            "status": "failed",
            "detail": {"missing": [c.model for c in result.blocking], "message": result.message()},
        },
    )
    ctx.emit("done", {"status": "failed", "failed_stages": ["preflight"]})
    return JobResult(status="failed", failed_stages=["preflight"])


def process_document(
    db: Database, storage: Storage, settings: Settings, doc_id: str, job_id: str
) -> JobResult:
    """Run the upload pipeline for one document (the worker's entry point).

    Preflight first: a missing model refuses the job unless the user ticked "analyse without it"
    (``doc.skipped_models``). The finished analysis is stamped with the pipeline version, the
    models fingerprint and a ``complete`` / ``degraded`` / ``failed`` status (CC-04).
    """
    ctx = JobContext(doc_id=doc_id, job_id=job_id, db=db, storage=storage, settings=settings)
    doc = db.get_doc(doc_id)
    skipped = list(doc.skipped_models) if doc else []
    pre = run_preflight(settings, skipped)
    if not pre.ok:
        return _refuse(ctx, pre)
    # Only a model that is really missing is skipped; a ticked one that came back runs normally.
    used_skips = [m for m in skipped if m in pre.missing]
    skip_stages = {s: m for m in used_skips for s in STAGES_NEEDING.get(m, ())}
    result = run_job(ctx, upload_stages(settings.jobs.model_stages), skip_stages)
    real_failures = [s for s in result.failed_stages if s not in skip_stages]
    status, reasons = analysis_status(result.status, real_failures, used_skips)
    fp = models_fingerprint(settings, skip=used_skips)
    db.update_doc(
        doc_id,
        analysis_status=status,
        degraded_reasons=reasons,
        pipeline_version=settings.pipeline_version,
        fingerprint=fp.value,
    )
    doc = db.get_doc(doc_id)
    if doc is not None and result.rejection is None:
        write_report(storage, doc, doc.companion_of)
    return result


__all__ = [
    "IST",
    "READY_PARTS",
    "SIMPLIFIED",
    "SOURCE",
    "InlineLauncher",
    "JobContext",
    "JobResult",
    "LaunchError",
    "Launcher",
    "SimplifyDrain",
    "Stage",
    "StageRejected",
    "StageTimeout",
    "UploadBlocked",
    "analysis_status",
    "auto_enqueue",
    "cache_key",
    "check_upload_allowed",
    "day_window",
    "delete_document",
    "load_simplified",
    "models_fingerprint",
    "process_document",
    "reset_for_reanalysis",
    "run_job",
    "run_preflight",
    "run_queue",
    "sweep",
    "upload_stages",
]
