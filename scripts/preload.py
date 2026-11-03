"""Preload offer documents through the running local app, one after another (final session).

    uv run python scripts/preload.py path/to/a.pdf path/to/b.pdf ...
    uv run python scripts/preload.py --list pdfs.txt          # one PDF path per line
    uv run python scripts/preload.py --dir "D:/RHPs"          # every *.pdf in a folder

Resumable: a PDF whose report is already ready, complete and on the current pipeline_version is
skipped, so the command can be stopped and started again. Prints the time per document and per
stage, and appends a row per document to ``data/preload_log.csv``. Start the API first
(``uv run python scripts/run_app.py --no-frontend`` raises the upload quotas).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from smoke_local import follow_job, get, upload  # noqa: E402

from finsight.core.config import get_settings  # noqa: E402
from finsight.core.ids import make_doc_id  # noqa: E402

LOG = ROOT / "data" / "preload_log.csv"


def pdfs_from(args: argparse.Namespace) -> list[Path]:
    """The PDF paths from the arguments, ``--list`` and ``--dir``, in order, without repeats."""
    paths = [Path(p) for p in args.pdfs]
    if args.list:
        lines = Path(args.list).read_text(encoding="utf-8").splitlines()
        paths += [Path(x.strip().strip('"')) for x in lines if x.strip() and not x.startswith("#")]
    if args.dir:
        paths += sorted(Path(args.dir).glob("*.pdf"))
    seen: set[Path] = set()
    return [p for p in paths if not (p in seen or seen.add(p))]  # type: ignore[func-returns-value]


def is_done(doc: dict | None, version: str) -> bool:  # type: ignore[type-arg]
    """Whether the stored report is ready, complete and made by this pipeline_version."""
    if not doc:
        return False
    d = doc.get("doc", {})
    return (
        d.get("status") == "ready"
        and d.get("analysis_status") == "complete"
        and d.get("pipeline_version") == version
    )


def main() -> int:
    """Upload each PDF that has no current report and wait for its pipeline."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("--list", help="a text file with one PDF path per line")
    ap.add_argument("--dir", help="a folder of PDFs")
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--limit-s", type=float, default=3600, help="max seconds per document")
    a = ap.parse_args()
    pdfs = pdfs_from(a)
    if not pdfs:
        ap.error("give PDF paths, --list or --dir")
    version = get_settings().pipeline_version
    client = httpx.Client(base_url=a.api, timeout=120)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    new_log = not LOG.exists()
    failed: list[str] = []
    t_all = time.perf_counter()
    with LOG.open("a", encoding="utf-8", newline="") as fh:
        log = csv.writer(fh)
        if new_log:
            log.writerow(["at", "pdf", "doc_id", "status", "analysis_status", "seconds", "stages"])
        for i, pdf in enumerate(pdfs, 1):
            head = f"[{i}/{len(pdfs)}] {pdf.name}"
            if not pdf.exists():
                print(f"{head}: file not found", flush=True)
                failed.append(str(pdf))
                continue
            doc_id = make_doc_id(hashlib.sha256(pdf.read_bytes()).hexdigest())
            if is_done(get(client, f"/api/docs/{doc_id}"), version):
                print(f"{head}: already done ({doc_id})", flush=True)
                continue
            t0 = time.perf_counter()
            try:
                doc_id, _ = upload(client, pdf)
                stages = follow_job(client, doc_id, a.limit_s)
            except Exception as exc:  # keep going: one bad PDF must not stop the batch
                print(f"{head}: error {type(exc).__name__}: {exc}", flush=True)
                failed.append(str(pdf))
                continue
            secs = time.perf_counter() - t0
            d = (get(client, f"/api/docs/{doc_id}") or {}).get("doc", {})
            status, analysis = d.get("status"), d.get("analysis_status")
            company = d.get("company") or ""
            print(f"{head}: {status}/{analysis} in {secs:.0f}s  {company}  ({doc_id})", flush=True)
            print("    " + "  ".join(f"{k} {v:.0f}s" for k, v in stages.items()), flush=True)
            log.writerow(
                [datetime.now(UTC).isoformat(timespec="seconds"), str(pdf), doc_id, status,
                 analysis, round(secs), ";".join(f"{k}={v}" for k, v in stages.items())]
            )  # fmt: skip
            fh.flush()
            if status != "ready":
                failed.append(str(pdf))
    print(f"done in {(time.perf_counter() - t_all) / 60:.1f} min; {len(failed)} failed", flush=True)
    for f in failed:
        print(f"  failed: {f}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
