"""E15: red-flag statuses against the status gold → ``eval_results/b/redflags.json``.

    uv run python scripts/redflag_eval.py --slice dev --allow-unverified   # tuning aid, dev only
    uv run python scripts/redflag_eval.py --slice all --final              # the E15 run, once

The status gold (``data/gold/redflag_status_gold.jsonl``, written by
``scripts/redflag_status_gold.py`` from verified gold v3 rows) holds 13 statuses per IPO. The
pipeline's statuses are what ``finsight.redflags`` computes from ``extract_summary`` on the same
document, so E15 measures the extraction plus the rules together (E14 measures extraction alone).
Reported: exact accuracy, accuracy where the gold has a value, the confusion matrix, per-check
accuracy and the serious disagreements (OK against Concern). Severe overrides are listed per IPO
for information; they are not part of the 13 statuses. C-ADR-02: only ``dev`` may be scored
before the final run, which needs every gold row spot-checked or verified.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

GOLD = ROOT / "data" / "gold" / "redflag_status_gold.jsonl"
OUT = ROOT / "eval_results" / "b" / "redflags.json"
STATUSES = ("ok", "watch", "concern", "not_available", "not_applicable")
ORDINAL = {"ok": 0, "watch": 1, "concern": 2}
DRAFT = "_unverified_draft"


def score_rows(
    gold: list[Mapping[str, Any]], predicted: Mapping[str, Mapping[str, str]]
) -> list[dict[str, Any]]:
    """One scored row per gold status: ``predicted`` is ``{ipo_id: {rf_id: status}}``."""
    out: list[dict[str, Any]] = []
    for g in gold:
        ipo, rf, want = str(g["ipo_id"]), str(g["rf"]), str(g["status"])
        got = predicted.get(ipo, {}).get(rf, "missing")
        serious = want in ORDINAL and got in ORDINAL and abs(ORDINAL[want] - ORDINAL[got]) == 2
        out.append(
            {"ipo_id": ipo, "rf": rf, "gold": want, "pred": got, "correct": want == got,
             "serious": serious}
        )  # fmt: skip
    return out


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Accuracy, accuracy on valued gold, confusion matrix, per-check accuracy."""
    n = len(rows) or 1
    valued = [r for r in rows if r["gold"] in ORDINAL]
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    per_rf: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        confusion[r["gold"]][r["pred"]] += 1
        per_rf[r["rf"]]["n"] += 1
        per_rf[r["rf"]]["correct"] += r["correct"]
    return {
        "n_rows": len(rows),
        "n_ipos": len({r["ipo_id"] for r in rows}),
        "accuracy": round(sum(r["correct"] for r in rows) / n, 3),
        "accuracy_on_valued_gold": (
            round(sum(r["correct"] for r in valued) / len(valued), 3) if valued else None
        ),
        "n_valued": len(valued),
        "serious_disagreements": sum(r["serious"] for r in rows),
        "confusion": {g: dict(c) for g, c in sorted(confusion.items())},
        "per_check": {
            k: {"n": c["n"], "accuracy": round(c["correct"] / c["n"], 3)}
            for k, c in sorted(per_rf.items())
        },
    }


def predict(processed: Path, ipo_id: str) -> tuple[dict[str, str], list[str]]:
    """Statuses (and severe override ids) the pipeline's rules give the IPO's RHP."""
    from summary_eval import load_summary

    from finsight.core.schemas import ParsedDoc, XRay
    from finsight.redflags import detect_severe, evaluate, inputs_from_summary
    from finsight.redflags.severe import with_auditor

    summary, _ = load_summary(processed, ipo_id, "rhp")
    if summary is None:
        return {}, []
    xray_path = processed / ipo_id / "xray.json"
    # The X-Ray carries the offer facts (price, fresh issue, OFS) that RF04 and RF05 compare
    # against; without it those two checks are "not available" whatever the document says.
    xray = XRay.model_validate_json(xray_path.read_bytes()) if xray_path.exists() else None
    inputs = inputs_from_summary(summary, xray)
    severe: list[str] = []
    parsed = processed / ipo_id / "parsed.json"
    sections_path = processed / ipo_id / "sections.json"
    if parsed.exists() and sections_path.exists():
        from summary_eval import SECTIONS

        doc = ParsedDoc.model_validate_json(parsed.read_bytes())
        found = detect_severe(doc, SECTIONS.validate_json(sections_path.read_bytes()), ipo_id)
        remark = next((v.evidence for v in summary.auditor_remarks if v.evidence), None)
        severe = [o.id for o in with_auditor(inputs.auditor == "qualified", found, remark)]
    return {f.id: f.status for f in evaluate(inputs).flags}, severe


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice", default="dev", choices=("dev", "test", "all"))
    ap.add_argument("--gold", type=Path, default=GOLD)
    ap.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--allow-unverified", action="store_true", help="dev only: a tuning draft")
    ap.add_argument("--final", action="store_true", help="the one E15 run on test/all slices")
    a = ap.parse_args(argv)
    demo = yaml.safe_load((ROOT / "configs" / "demo_ipos.yaml").read_text(encoding="utf-8"))
    split = {e["ipo_id"]: e["split"] for e in demo["ipos"]}
    if a.slice != "dev" and not a.final:
        ap.error("C-ADR-02: test documents are scored once, with --final")
    if a.slice != "dev" and a.allow_unverified:
        ap.error("the final E15 run needs a verified status gold")
    if not a.gold.exists():
        ap.error(
            f"{a.gold} not found: run scripts/redflag_status_gold.py after gold v3 is verified"
        )
    gold = [json.loads(x) for x in a.gold.read_text(encoding="utf-8").splitlines() if x.strip()]
    gold = [g for g in gold if a.slice == "all" or split.get(str(g["ipo_id"])) == a.slice]
    draft = any(DRAFT in str(g.get("label_source")) for g in gold)
    if draft and not a.allow_unverified:
        ap.error(
            "the status gold is an unverified draft; verify gold v3 or pass --allow-unverified"
        )
    predicted: dict[str, dict[str, str]] = {}
    overrides: dict[str, list[str]] = {}
    for ipo in sorted({str(g["ipo_id"]) for g in gold}):
        predicted[ipo], overrides[ipo] = predict(a.processed, ipo)
    rows = score_rows(gold, predicted)
    result = {
        "experiment": "E15 red-flag statuses",
        "slice": a.slice,
        "final": a.final,
        "draft": draft,
        "written_by": "scripts/redflag_eval.py",
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": summarise(rows),
        "severe_overrides": overrides,
        "rows": rows,
    }
    out = a.out or (OUT if a.final else OUT.with_name(f"redflags_{a.slice}_draft.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n")
    print(f"wrote {out}: accuracy {result['summary']['accuracy']} over {len(rows)} statuses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
