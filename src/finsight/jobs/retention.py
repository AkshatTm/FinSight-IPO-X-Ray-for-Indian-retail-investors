"""Retention sweep: delete non-showcase documents 30 days after upload (B02 §9).

Files and rows go; the ``uploads`` rows stay so daily quotas remain correct. A later upload of
the same file is processed again from scratch.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from finsight.db import Database, utcnow
from finsight.storage import Storage


def sweep(
    db: Database, storage: Storage, retention_days: int, now: datetime | None = None
) -> list[str]:
    """Delete expired documents and return their ids."""
    cutoff = (now or utcnow()) - timedelta(days=retention_days)
    expired = db.expired_docs(cutoff)
    for doc_id in expired:
        storage.delete_prefix(f"docs/{doc_id}/")
        db.delete_doc_rows(doc_id)
    return expired
