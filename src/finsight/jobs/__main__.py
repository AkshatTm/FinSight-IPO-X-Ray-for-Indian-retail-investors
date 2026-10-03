"""Worker entry point: ``python -m finsight.jobs run <doc_id> <job_id>`` (Cloud Run Job, B3.3a)
and ``python -m finsight.jobs sweep`` (retention)."""

from __future__ import annotations

import os
import sys

from finsight.core.config import get_settings
from finsight.db import make_database
from finsight.jobs import process_document, sweep
from finsight.storage import make_storage


def main(argv: list[str]) -> int:
    settings = get_settings()
    db, storage = make_database(settings), make_storage(settings)
    if argv[:1] == ["run"]:
        doc_id = argv[1] if len(argv) > 1 else os.environ["DOC_ID"]
        job_id = argv[2] if len(argv) > 2 else os.environ["JOB_ID"]
        result = process_document(db, storage, settings, doc_id, job_id)
        print(f"{doc_id}: {result.status}")
        return 0 if result.status != "failed" or result.rejection else 1
    if argv[:1] == ["sweep"]:
        deleted = sweep(db, storage, settings.uploads.retention_days)
        print(f"deleted {len(deleted)} expired documents")
        return 0
    print("usage: python -m finsight.jobs run <doc_id> <job_id> | sweep", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
