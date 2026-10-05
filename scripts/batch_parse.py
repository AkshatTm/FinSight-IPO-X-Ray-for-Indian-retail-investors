"""Run the upload stages over every downloaded document of the universe (C1.3).

    uv run python scripts/batch_parse.py [--limit 3] [--only ipo-id ...] [--retry-failed]
    uv run python scripts/batch_parse.py --apply        # write outcomes into configs/ipo_universe.csv
    uv run python scripts/batch_parse.py --report       # write eval_results/c/parse_batch.json

One document at a time, resumable (state in data/processed/batch/state.json, gitignored). Reads
`configs/ipo_universe.csv` without changing it until `--apply`, so it can run while the fetch
script is still downloading. Validation limits are loosened (200 MB, 3000 pages): the product
limits (50 MB, 1500 pages) are reported in the results instead of silently dropping documents.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.core.config import load_settings  # noqa: E402
from finsight.ingest.fetch import read_rows, write_rows  # noqa: E402
from finsight.pipeline.batch import apply_results, load_state, run_batch  # noqa: E402

CSV = ROOT / "configs" / "ipo_universe.csv"
PDFS = ROOT / "data" / "raw" / "offer_docs"
WORK = ROOT / "data" / "processed" / "batch"
STATE = WORK / "state.json"
REPORT = ROOT / "eval_results" / "c" / "parse_batch.json"
PRODUCT_MAX_MB, PRODUCT_MAX_PAGES = 50, 1500


def summary(state_path: Path) -> dict:
    """Aggregate numbers for ``parse_batch.json`` (no document text)."""
    state = load_state(state_path)
    results = list(state.values())
    times = sorted(r.wall_s for r in results if r.wall_s)
    pages = [r.pages for r in results if r.pages]
    stage_totals: Counter[str] = Counter()
    for r in results:
        stage_totals.update(r.timings_s)
    return {
        "written_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_documents": len(results),
        "status": dict(Counter(r.status for r in results)),
        "excluded_reasons": dict(Counter(r.reason for r in results if r.status == "excluded")),
        "failed_reasons": dict(Counter(r.reason for r in results if r.status == "failed")),
        "wall_seconds": {
            "median": times[len(times) // 2] if times else None,
            "max": times[-1] if times else None,
            "total": round(sum(times), 1),
        },
        "stage_seconds_total": {k: round(v, 1) for k, v in stage_totals.items()},
        "peak_rss_mb_max": max((r.peak_rss_mb for r in results), default=None),
        "output_bytes_total": sum(r.output_bytes for r in results),
        "pages_median": sorted(pages)[len(pages) // 2] if pages else None,
        "over_product_page_limit": sorted(
            r.ipo_id for r in results if r.pages and r.pages > PRODUCT_MAX_PAGES
        ),
        "documents": {
            r.ipo_id: {
                "status": r.status, "reason": r.reason, "pages": r.pages, "n_risks": r.n_risks,
                "wall_s": r.wall_s, "peak_rss_mb": r.peak_rss_mb, "output_bytes": r.output_bytes,
            }
            for r in results
        },
    }  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=CSV)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    if a.apply:
        rows = read_rows(a.csv)
        n = apply_results(rows, load_state(STATE))
        write_rows(a.csv, rows)
        print(f"updated {n} rows in {a.csv.name}")
        return 0
    if a.report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(summary(STATE), indent=1) + "\n", encoding="utf-8")
        print("wrote", REPORT.relative_to(ROOT))
        return 0
    settings = load_settings("dev_light")
    settings = settings.model_copy(
        update={"uploads": settings.uploads.model_copy(update={"max_mb": 200, "max_pages": 3000})}
    )
    state = run_batch(
        read_rows(a.csv), PDFS, WORK, settings, STATE,
        only=set(a.only) if a.only else None, limit=a.limit, retry_failed=a.retry_failed,
    )  # fmt: skip
    print(Counter(r.status for r in state.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
