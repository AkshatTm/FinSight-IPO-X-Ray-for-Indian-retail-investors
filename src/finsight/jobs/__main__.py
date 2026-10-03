"""Worker entry point (Cloud Run Jobs, B3.3a).

- ``python -m finsight.jobs run [<doc_id> <job_id>]``: every stage of one document. Cloud Run
  passes the ids as ``DOC_ID`` / ``JOB_ID`` env overrides (``jobs.launcher``).
- ``python -m finsight.jobs simplify [<doc_id>]``: queue the top ``simplify.auto_top_n`` risks by
  importance, then drain the simplification queue (the L4 GPU job, or the CPU job's fallback).
- ``python -m finsight.jobs sweep``: delete documents past retention (scheduled job).
"""

from __future__ import annotations

import os
import sys
from typing import Any

from finsight.core.config import Settings, get_settings
from finsight.db import Database, make_database
from finsight.jobs import auto_enqueue, process_document, run_queue, sweep
from finsight.storage import Storage, doc_key, get_json, make_storage


def simplify_document(
    db: Database, storage: Storage, settings: Settings, doc_id: str, simplifier: Any = None
) -> dict[str, int]:
    """Queue the most important risks and rewrite everything queued for ``doc_id``.

    Events go to the document's latest job, so the report page sees ``risk_simplified`` as each
    rewrite lands.
    """
    from finsight.core.schemas import Risk
    from finsight.risks import make_simplifier, ranked_rids

    risks = [Risk.model_validate(r) for r in get_json(storage, doc_key(doc_id, "risks.json"))]
    auto_enqueue(db, doc_id, ranked_rids(risks), settings.simplify.auto_top_n)
    if simplifier is None:
        simplifier = make_simplifier(settings.simplify, settings.paths.models_dir)
    job = db.latest_job(doc_id)

    def emit(event: str, data: dict[str, Any]) -> int:
        return db.append_event(job.job_id, event, data) if job else 0

    by_rid = {r.rid: (r.title, r.body) for r in risks}
    return run_queue(db, storage, doc_id, by_rid, simplifier, emit)


def main(argv: list[str]) -> int:
    """Worker entry point: ``run``, ``simplify`` or ``sweep`` (ids from args or env)."""
    settings = get_settings()
    db, storage = make_database(settings), make_storage(settings)
    if argv[:1] == ["run"]:
        doc_id = argv[1] if len(argv) > 1 else os.environ["DOC_ID"]
        job_id = argv[2] if len(argv) > 2 else os.environ["JOB_ID"]
        result = process_document(db, storage, settings, doc_id, job_id)
        print(f"{doc_id}: {result.status}")
        return 0 if result.status != "failed" or result.rejection else 1
    if argv[:1] == ["simplify"]:
        doc_id = argv[1] if len(argv) > 1 else os.environ["DOC_ID"]
        counts = simplify_document(db, storage, settings, doc_id)
        print(f"{doc_id}: " + " ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        return 0
    if argv[:1] == ["sweep"]:
        deleted = sweep(db, storage, settings.uploads.retention_days)
        print(f"deleted {len(deleted)} expired documents")
        return 0
    print("usage: python -m finsight.jobs run | simplify | sweep", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
