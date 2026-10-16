"""Build the full report of every showcase IPO's RHP through the running local app (C3.5).

    uv run python scripts/build_showcase.py [--api http://127.0.0.1:8000] [--only ipo-id ...]

The library then shows a "Full report" link on each card. Reports are the ordinary upload
reports (same pipeline, same models) of the RHP in ``data/raw/rhp/``: the id of the report is the
RHP's ``doc_id``. Already finished reports are skipped; about 4 to 6 minutes per document.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from smoke_local import follow_job, get, upload  # noqa: E402

from finsight.ingest.registry import list_demo_ipos  # noqa: E402


def main() -> int:
    """Upload each showcase RHP that has no report yet and wait for its pipeline."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    client = httpx.Client(base_url=a.api, timeout=60)
    failed = []
    for ipo in list_demo_ipos():
        if a.only and ipo.ipo_id not in a.only:
            continue
        doc = get(client, f"/api/docs/{ipo.rhp.doc_id}")
        if doc and doc["doc"]["status"] in ("ready", "partial"):
            print(f"{ipo.ipo_id}: report exists ({doc['doc']['status']})", flush=True)
            continue
        t0 = time.perf_counter()
        doc_id, _ = upload(client, ipo.rhp.file)
        follow_job(client, doc_id, 3600)
        status = (get(client, f"/api/docs/{doc_id}") or {}).get("doc", {}).get("status")
        print(f"{ipo.ipo_id}: {status} in {time.perf_counter() - t0:.0f}s ({doc_id})", flush=True)
        if status not in ("ready", "partial"):
            failed.append(ipo.ipo_id)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
