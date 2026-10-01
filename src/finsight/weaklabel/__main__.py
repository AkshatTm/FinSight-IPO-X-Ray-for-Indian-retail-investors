"""Build the weak-label dataset from the corpus.

    uv run python -m finsight.weaklabel build [--force-audit]
    uv run python -m finsight.weaklabel audit-score     # E1 from the labelled audit file

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
from finsight.weaklabel.audit import sample_audit, score_audit, write_audit
from finsight.weaklabel.build_squad import build_dataset

LABEL_VERSION = 2  # v1 was audited (45/50); v2 applies the fixes from that audit (ADR-041)
AUDITED_VERSION = 1


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
    sub.add_parser("audit-score", help="labelled audit file -> eval_results/weaklabel_audit.json")
    args = parser.parse_args(argv)

    s = get_settings()
    audit_path = s.paths.gold_dir / "weaklabel_audit.jsonl"
    if args.command == "audit-score":
        labelled = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines() if x]
        result = {
            "experiment": "E1",
            "name": "weaklabel_audit",
            "measured_on": f"v{AUDITED_VERSION}",
            "current_label_version": f"v{LABEL_VERSION}",
            **score_audit(labelled),
            "notes": "Measured on v1 labels; the misses were fixed in v2, which is not re-audited.",
        }
        out = s.paths.eval_dir / "weaklabel_audit.json"
        out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({k: result[k] for k in ("n", "correct", "precision", "wilson_95")}))
        return 0

    out_dir = s.paths.processed_dir / "weaklabel"
    excel = excel_rows(s.paths.raw_dir / "ipo_dataset" / EXCEL_NAME)
    card = build_dataset(s.paths.processed_dir / "corpus", out_dir, excel, excluded_names())
    card = {"label_version": LABEL_VERSION, **card}
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
        path = write_audit(audit_path, sample_audit(rows), args.force_audit)
        print(f"audit sample: {path}")
    except FileExistsError as exc:
        print(exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
