"""The stage runner: run a document's stages in order, record B06 events, keep partial results.

Stages are idempotent: a stage whose output file already exists is not run again (a retried job
continues where it stopped). A failing stage marks the report ``partial`` and skips the stages
that need it; a failing *critical* stage (validation, parsing) fails the whole job.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from finsight.core.config import Settings
from finsight.core.logging import get_logger
from finsight.core.schemas import RejectionCode
from finsight.db import Database, utcnow
from finsight.storage import Storage, doc_key

logger = get_logger("finsight.jobs")

# B06 §2: which `ready` part each stage unlocks.
READY_PARTS: dict[str, str] = {
    "facts": "facts",
    "redflags": "redflags",
    "risks_scored": "risks",
    "risk_level": "risk_level",
    "compare": "compare",
    "index": "chat",
}


class StageRejected(Exception):
    """The upload is not processable (B06 rejection codes); the job ends as ``failed``."""

    def __init__(self, code: RejectionCode, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass
class JobContext:
    """What a stage may use. ``emit`` appends a B06 event to the job's stream."""

    doc_id: str
    job_id: str
    db: Database
    storage: Storage
    settings: Settings
    scratch: dict[str, Any] = field(default_factory=dict)  # in-memory hand-over between stages

    def emit(self, event: str, data: dict[str, Any]) -> int:
        """Append a job event and return its ``seq``."""
        return self.db.append_event(self.job_id, event, data)

    def key(self, name: str) -> str:
        """The storage key ``docs/<doc_id>/<name>``."""
        return doc_key(self.doc_id, name)


StageFn = Callable[[JobContext], dict[str, Any] | None]


@dataclass(frozen=True)
class Stage:
    """One pipeline step (B02 §3.1). ``output`` makes it idempotent; ``requires`` gates it."""

    name: str
    fn: StageFn
    output: str | None = None
    requires: tuple[str, ...] = ()
    critical: bool = False


@dataclass(frozen=True)
class JobResult:
    """How a job ended: ready, partial or failed, plus any rejection code."""

    status: str  # ready | partial | failed
    failed_stages: list[str]
    rejection: RejectionCode | None = None


def run_job(ctx: JobContext, stages: Sequence[Stage]) -> JobResult:
    """Run ``stages`` for ``ctx.doc_id`` and return the final status (also stored and emitted)."""
    db = ctx.db
    db.update_job(ctx.job_id, status="running", started_at=utcnow())
    failed: list[str] = []
    timings: dict[str, float] = {}
    rejection: RejectionCode | None = None
    fatal = False
    for stage in stages:
        if fatal:
            break
        missing = [name for name in stage.requires if name in failed]
        if missing:
            failed.append(stage.name)
            ctx.emit(
                "stage",
                {"stage": stage.name, "status": "failed", "detail": {"skipped_because": missing}},
            )
            continue
        db.update_job(ctx.job_id, stage=stage.name)
        if stage.output and ctx.storage.exists(ctx.key(stage.output)):
            ctx.emit("stage", {"stage": stage.name, "status": "end", "detail": {"cached": True}})
            _ready(ctx, stage.name)
            continue
        ctx.emit("stage", {"stage": stage.name, "status": "start"})
        start = time.perf_counter()
        try:
            detail = stage.fn(ctx) or {}
        except StageRejected as err:
            rejection, fatal = err.code, True
            failed.append(stage.name)
            ctx.emit(
                "stage", {"stage": stage.name, "status": "failed", "detail": {"reason": err.code}}
            )
            continue
        except Exception as err:  # a stage failure must not kill the job
            logger.exception(
                "stage %s failed for %s",
                stage.name,
                ctx.doc_id,
                extra={"doc_id": ctx.doc_id, "job_id": ctx.job_id, "stage": stage.name},
            )
            failed.append(stage.name)
            fatal = stage.critical
            ctx.emit(
                "stage",
                {"stage": stage.name, "status": "failed", "detail": {"error": type(err).__name__}},
            )
            continue
        timings[stage.name] = round(time.perf_counter() - start, 3)
        ctx.emit("stage", {"stage": stage.name, "status": "end", "detail": detail})
        _ready(ctx, stage.name)

    status = "failed" if fatal else ("partial" if failed else "ready")
    db.update_doc(ctx.doc_id, status=status, rejection=rejection)
    db.update_job(
        ctx.job_id,
        status="failed" if fatal else "done",
        finished_at=utcnow(),
        error=rejection or (",".join(failed) or None),
        progress={"timings_s": timings, "failed_stages": failed},
    )
    ctx.emit("done", {"status": status, "failed_stages": failed})
    return JobResult(status=status, failed_stages=failed, rejection=rejection)


def _ready(ctx: JobContext, stage: str) -> None:
    part = READY_PARTS.get(stage)
    if part:
        ctx.emit("ready", {"part": part})
