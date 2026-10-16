"""C1.5: download the BIR spreadsheet links that still answer as direct PDFs.

    uv run python scripts/backfill_bir_pdfs.py [--limit N]
    # -> data/raw/bir_backfill/<mapping_key>.pdf and data/raw/bir_backfill/index.json

Only links that answer HTTP 2xx with a PDF content type (or a ``.pdf`` path) are fetched, one request
each with a pause. The folder is new and nothing reads it: no split, manifest or eval set changes
(C-ADR-02); a later part may parse these files. ``eval_results/c/bir_backfill.json`` records the
file counts before and after.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "raw" / "bir_backfill"
OUT = ROOT / "eval_results" / "c" / "bir_backfill.json"

import importlib.util  # noqa: E402
import sys  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "check_bir_links", ROOT / "scripts" / "check_bir_links.py"
)
assert _spec is not None
assert _spec.loader is not None
chk = importlib.util.module_from_spec(_spec)
sys.modules["check_bir_links"] = chk
_spec.loader.exec_module(chk)


def _safe(key: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:120]


def main() -> None:
    """Probe every link once, download the live PDFs, write the index and the counts."""
    from openpyxl import load_workbook

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pause", type=float, default=0.5)
    ap.add_argument("--dest", type=Path, default=DEST, help="folder for the PDFs")
    a = ap.parse_args()

    ws = load_workbook(chk.XLSX, read_only=True).worksheets[0]
    rows = ws.iter_rows(values_only=True)
    idx = {h: i for i, h in enumerate(next(rows))}
    jobs: list[tuple[str, str, str]] = []
    for row in rows:
        links: list[str] = []
        for col in chk.LINK_COLUMNS:
            links += chk.extract_links(row[idx[col]])
        for url in dict.fromkeys(links):
            jobs.append((str(row[idx["mapping_key"]]), str(row[idx["Close Year"]] or "")[:4], url))
    if a.limit:
        jobs = jobs[: a.limit]

    dest = a.dest
    dest.mkdir(parents=True, exist_ok=True)
    before = len(list(dest.glob("*.pdf")))
    index, skipped = [], 0
    for key, year, url in jobs:
        target = dest / f"{_safe(key)}.pdf"
        if target.exists():
            continue
        status, ctype = chk.probe(url)
        live = status is not None and 200 <= status < 300
        if not (live and ("pdf" in ctype.lower() or url.lower().split("?")[0].endswith(".pdf"))):
            skipped += 1
            time.sleep(a.pause)
            continue
        req = urllib.request.Request(url, headers={"User-Agent": chk.UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
        except Exception as err:
            print("download failed", key, type(err).__name__, flush=True)
            continue
        if not data.startswith(b"%PDF"):
            print("not a PDF", key, flush=True)
            continue
        target.write_bytes(data)
        index.append({"mapping_key": key, "close_year": year, "url": url, "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})  # fmt: skip
        print("saved", target.name, len(data), flush=True)
        time.sleep(a.pause)
    old = (
        json.loads((dest / "index.json").read_text("utf-8"))
        if (dest / "index.json").exists()
        else []
    )
    (dest / "index.json").write_text(json.dumps(old + index, indent=1), encoding="utf-8")
    after = len(list(dest.glob("*.pdf")))
    summary = {
        "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "links_checked": len(jobs),
        "pdf_files_before": before,
        "pdf_files_after": after,
        "downloaded_now": len(index),
        "not_direct_pdf_or_dead": skipped,
        "total_mb": round(sum(p.stat().st_size for p in dest.glob("*.pdf")) / 2**20, 1),
        "destination": "data/raw/bir_backfill/ (gitignored; read by nothing yet)",
        "splits_or_eval_sets_changed": False,
    }
    OUT.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
