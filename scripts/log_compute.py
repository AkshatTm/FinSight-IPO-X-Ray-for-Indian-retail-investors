"""Append Colab/Kaggle ``run_summary.json`` files to ``eval_results/c/compute_log.jsonl`` (C03 §2.4).

    uv run python scripts/log_compute.py path/to/run_summary.json [more.json ...]
    uv run python scripts/log_compute.py --manual --job rate_check --gpu-class L4 \
        --units-per-hour 1.54 --note "Colab Pro Resources panel"

Rows are validated against REQUIRED_KEYS and de-duplicated on (job, finished_utc, gpu_class). Records keep
their timestamps (honesty rule); nothing here is hand-edited result data: manual rows say so.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "eval_results" / "c" / "compute_log.jsonl"
REQUIRED_KEYS = ("job", "finished_utc", "gpu_class")


def validate(row: dict[str, Any]) -> None:
    """Raise ``ValueError`` when a row lacks a required key."""
    missing = [k for k in REQUIRED_KEYS if not row.get(k)]
    if missing:
        raise ValueError(f"run summary missing {missing}")


def read_log(log: Path = LOG) -> list[dict[str, Any]]:
    """All rows currently in the log."""
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]


def append_rows(rows: list[dict[str, Any]], log: Path = LOG) -> int:
    """Validate and append rows not yet logged; returns how many were added."""
    seen = {(r["job"], r["finished_utc"], r["gpu_class"]) for r in read_log(log)}
    added = 0
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            validate(row)
            key = (row["job"], row["finished_utc"], row["gpu_class"])
            if key in seen:
                continue
            seen.add(key)
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            added += 1
    return added


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--log", type=Path, default=LOG)
    ap.add_argument(
        "--manual", action="store_true", help="log a hand-measured rate (no run_summary.json)"
    )
    ap.add_argument("--job")
    ap.add_argument("--gpu-class")
    ap.add_argument("--units-per-hour", type=float)
    ap.add_argument("--note", default="")
    ap.add_argument("--extra", default="{}", help="JSON object merged into a manual row")
    a = ap.parse_args(argv)
    rows: list[dict[str, Any]] = []
    if a.manual:
        if not (a.job and a.gpu_class and a.units_per_hour is not None):
            ap.error("--manual needs --job, --gpu-class and --units-per-hour")
        rows.append(
            {
                "job": a.job,
                "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                "gpu_class": a.gpu_class,
                "units_per_hour_observed": a.units_per_hour,
                "source": "manual (Colab Resources panel / nvidia-smi, read by Akshat)",
                "note": a.note,
                **json.loads(a.extra),
            }
        )
    for f in a.files:
        rows.append(json.loads(f.read_text(encoding="utf-8")))
    if not rows:
        ap.error("nothing to log")
    print(f"logged {append_rows(rows, a.log)} row(s) -> {a.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
