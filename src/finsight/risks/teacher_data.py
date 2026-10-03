"""After the teacher run (local): filter the raw answers, write the training files, sample the
quality sheet (B03 §3.3–3.5).

    uv run python -m finsight.risks.teacher_data filter \\
        --risks data/processed/teacher/risks.jsonl --raw data/processed/teacher/raw.jsonl
    uv run python -m finsight.risks.teacher_data sheet   # 100 rows for Akshat to rate

Inputs and outputs live in ``data/processed/teacher/`` (gitignored). The drop report is the
only file meant for ``eval_results/`` and it is written by this code, never by hand.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Any

from finsight.risks.filters import FilterReport, Kept, TeacherItem, filter_outputs
from finsight.risks.teacher import PROMPT_VERSION
from finsight.risks.teacher_run import read_jsonl

SHEET_SEED = 2026
SHEET_COLUMNS = (
    "risk_id",
    "company",
    "original",
    "simple",
    "category",
    "seriousness_1to5",
    "hard_fact",
    "faithful",  # Akshat: yes | partly | no
    "category_correct",  # Akshat: yes | no (+ the right category in notes)
    "notes",
    "label_source",
)


def original_text(risk: dict[str, Any]) -> str:
    """The text the teacher saw (same layout as ``teacher.messages``)."""
    title, body = str(risk.get("title") or "").strip(), str(risk["body"]).strip()
    return f"Title: {title}\n\n{body}" if title else body


def filter_file(risks_path: Path, raw_path: Path) -> tuple[FilterReport, dict[str, Any]]:
    """Join raw answers to their risks and run the filters. Unknown ``risk_id`` rows are skipped."""
    risks = {str(r["risk_id"]): r for r in read_jsonl(risks_path)}
    items, meta = [], {}
    for row in read_jsonl(raw_path):
        risk = risks.get(str(row["risk_id"]))
        if risk is None:
            continue
        meta = {k: row[k] for k in ("model", "prompt_version") if k in row} or meta
        items.append(TeacherItem(str(row["risk_id"]), original_text(risk), str(row["raw"])))
    return filter_outputs(items), meta


def label_source(meta: dict[str, Any]) -> str:
    """``teacher:<model>:<prompt version>`` for AI-assisted labels."""
    return f"teacher:{meta.get('model', 'unknown')}:{meta.get('prompt_version', PROMPT_VERSION)}"


def write_outputs(
    report: FilterReport, meta: dict[str, Any], risks_path: Path, out_dir: Path
) -> dict[str, Path]:
    """``labels.jsonl`` (classifier), ``simplify.jsonl`` (student) and ``filter_report.json``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    companies = {str(r["risk_id"]): r.get("company", "") for r in read_jsonl(risks_path)}
    source = label_source(meta)
    paths = {
        "labels": out_dir / "labels.jsonl",
        "simplify": out_dir / "simplify.jsonl",
        "report": out_dir / "filter_report.json",
    }
    with (
        paths["labels"].open("w", encoding="utf-8") as lab,
        paths["simplify"].open("w", encoding="utf-8") as sim,
    ):
        for k in report.kept:
            base = {"risk_id": k.risk_id, "company": companies.get(k.risk_id, "")}
            o = k.output
            lab.write(
                json.dumps(
                    {
                        **base,
                        "category": o.category,
                        "seriousness_1to5": o.seriousness_1to5,
                        "hard_fact": o.hard_fact,
                        "label_source": source,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            sim.write(
                json.dumps(
                    {**base, "original": k.original, "simple": o.simple, "label_source": source},
                    ensure_ascii=False,
                )
                + "\n"
            )
    summary = {**report.summary(), "label_source": source}
    paths["report"].write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return paths


def quality_sheet(
    kept: list[Kept], companies: dict[str, str], meta: dict[str, Any], n: int = 100
) -> list[dict[str, Any]]:
    """``n`` kept outputs, sampled with a fixed seed, with blank rating columns."""
    rng = random.Random(SHEET_SEED)
    pick = sorted(rng.sample(range(len(kept)), min(n, len(kept))))
    source = label_source(meta)
    rows = []
    for i in pick:
        k = kept[i]
        rows.append(
            {
                "risk_id": k.risk_id,
                "company": companies.get(k.risk_id, ""),
                "original": k.original,
                "simple": k.output.simple,
                "category": k.output.category,
                "seriousness_1to5": k.output.seriousness_1to5,
                "hard_fact": k.output.hard_fact,
                "faithful": "",
                "category_correct": "",
                "notes": "",
                "label_source": source,
            }
        )
    return rows


def write_sheet(rows: list[dict[str, Any]], path: Path) -> None:
    """Write the quality-check sheet as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> None:
    """CLI: ``filter`` the teacher replies or write the quality ``sheet``."""
    p = argparse.ArgumentParser(prog="python -m finsight.risks.teacher_data")
    p.add_argument("command", choices=["filter", "sheet"])
    p.add_argument("--dir", type=Path, default=Path("data/processed/teacher"))
    p.add_argument("--risks", type=Path)
    p.add_argument("--raw", type=Path)
    p.add_argument("-n", type=int, default=100)
    args = p.parse_args(argv)
    risks = args.risks or args.dir / "risks.jsonl"
    raw = args.raw or args.dir / "raw.jsonl"
    report, meta = filter_file(risks, raw)
    if args.command == "filter":
        paths = write_outputs(report, meta, risks, args.dir)
        print(json.dumps(report.summary()["dropped"]), "kept", len(report.kept))
        print("wrote", ", ".join(str(p) for p in paths.values()))
    else:
        companies = {str(r["risk_id"]): r.get("company", "") for r in read_jsonl(risks)}
        out = args.dir / "quality_sheet.csv"
        write_sheet(quality_sheet(report.kept, companies, meta, args.n), out)
        print("wrote", out)


if __name__ == "__main__":
    main()
