"""Build the weak-label dataset from the corpus.

    uv run python -m finsight.weaklabel build [--force-audit]

Writes ``data/processed/weaklabel/{train,dev}.jsonl`` (git-ignored), the dataset card
``eval_results/weaklabel_stats.json`` and the audit sample ``data/gold/weaklabel_audit.jsonl``.
Only allow-listed Excel columns are read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import openpyxl

from finsight.core.config import get_settings
from finsight.ingest.corpus import EXCEL_NAME
from finsight.ingest.exclusion import excluded_names
from finsight.ingest.recon import ALLOWED_COLUMNS, SHEET
from finsight.weaklabel.audit import sample_audit, write_audit
from finsight.weaklabel.build_squad import build_dataset


def excel_rows(path: Path) -> dict[str, dict[str, str | None]]:
    """``mapping_key -> {allowed column: text}``; other columns are never read into memory."""
    wb = openpyxl.load_workbook(path, read_only=True)
    it = wb[SHEET].iter_rows(values_only=True)
    header = [str(h) for h in next(it)]
    keep = {i: name for i, name in enumerate(header) if name in ALLOWED_COLUMNS}
    rows: dict[str, dict[str, str | None]] = {}
    for raw in it:
        row = {name: (None if raw[i] is None else str(raw[i]).strip()) for i, name in keep.items()}
        if row.get("mapping_key"):
            rows[str(row["mapping_key"])] = row
    wb.close()
    return rows


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.weaklabel")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="corpus -> SQuAD 2.0 train/dev + stats + audit sample")
    build.add_argument("--force-audit", action="store_true", help="replace an existing audit file")
    args = parser.parse_args(argv)

    s = get_settings()
    out_dir = s.paths.processed_dir / "weaklabel"
    excel = excel_rows(s.paths.raw_dir / "ipo_dataset" / EXCEL_NAME)
    card = build_dataset(s.paths.processed_dir / "corpus", out_dir, excel, excluded_names())
    stats_path = s.paths.eval_dir / "weaklabel_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(card, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: card[k] for k in ("n_ipos", "seed_coverage", "train", "dev")}, indent=1))

    rows: list[dict[str, Any]] = [
        json.loads(line)
        for name in ("train.jsonl", "dev.jsonl")
        for line in (out_dir / name).read_text(encoding="utf-8").splitlines()
    ]
    try:
        path = write_audit(s.paths.gold_dir / "weaklabel_audit.jsonl", sample_audit(rows),
                           args.force_audit)  # fmt: skip
        print(f"audit sample: {path}")
    except FileExistsError as exc:
        print(exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
