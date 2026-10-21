"""One-off cleanup (CC-04): delete every stored analysis with a degraded status or an unknown
fingerprint, so it is analysed again from scratch the next time its PDF is uploaded.

    uv run python scripts/purge_degraded.py            # dry run: lists what would go
    uv run python scripts/purge_degraded.py --apply    # deletes (files, indexes, page images, rows)

Showcase documents and anything still processing are never touched. Failed uploads that were
rejected (scanned, password, ...) have nothing to purge but their row; they count as failed.
"""

from __future__ import annotations

import argparse
import sys

from finsight.core.config import Settings, get_settings
from finsight.core.schemas import DocRecord
from finsight.db import Database, make_database
from finsight.jobs import delete_document
from finsight.storage import Storage, make_storage


def reason(doc: DocRecord) -> str | None:
    """Why this analysis should go, or ``None`` to keep it."""
    if doc.is_showcase or doc.status in ("uploading", "processing"):
        return None
    if doc.analysis_status in ("degraded", "failed"):
        return f"{doc.analysis_status}: {', '.join(doc.degraded_reasons) or 'no reason stored'}"
    if doc.fingerprint is None:
        return "unknown fingerprint (made before cache v2, or never finished)"
    return None


def purge(db: Database, storage: Storage, settings: Settings, apply: bool) -> list[tuple[str, str]]:
    """The ``(doc_id, reason)`` pairs found; deleted when ``apply``."""
    found = [(d.doc_id, why) for d in db.all_docs() if (why := reason(d)) is not None]
    if apply:
        for doc_id, _ in found:
            delete_document(db, storage, settings, doc_id)
    return found


def main(argv: list[str]) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="delete (default: dry run)")
    args = parser.parse_args(argv)
    settings = get_settings()
    found = purge(make_database(settings), make_storage(settings), settings, args.apply)
    for doc_id, why in found:
        print(f"{'deleted' if args.apply else 'would delete'} {doc_id}: {why}")
    print(f"{len(found)} analyses {'deleted' if args.apply else 'found (dry run; use --apply)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
