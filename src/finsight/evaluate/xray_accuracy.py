"""System accuracy of the X-Ray under two extractor configurations (G2 decision, ADR-018).

    uv run python -m finsight.evaluate.xray_accuracy

The ladder (``run_gold``) scores each extractor alone. The product shows the X-Ray, where one
extractor is primary and another only confirms or doubts it. This builds the X-Ray of every demo
IPO from the saved candidates under

- ``rules_first``: ``fields.yaml`` as shipped (rules primary, fine-tuned model as cross-check);
- ``dev_choice``: the first choice ADR-018 made on the dev IPOs alone (fresh issue size and total
  issue size with the fine-tuned model primary, rules as cross-check),

and scores the chosen value of each ladder field against gold by NVM. The product choice
(``rules_first``) was made after seeing test results, so the number is reported beside the
dev-only choice, and a clean re-check on gold v2 is planned (P5.1).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.core.schemas import FieldSpec, XRay
from finsight.evaluate.metrics import bootstrap_ci, nvm, paired_bootstrap
from finsight.evaluate.run_gold import SPLITS, gold_value, ladder_rows
from finsight.extract import build_xray, load_fields
from finsight.ingest.registry import list_demo_ipos
from finsight.pipeline.xray_stage import load_inputs

DEV_CHOICE_FIELDS = ("fresh_issue_size", "total_issue_size")  # ADR-018 as first decided on dev
CONFIGS = ("rules_first", "dev_choice")
BUILT_AT = datetime(2026, 10, 1, tzinfo=UTC)


def config_fields(config: str, shipped: list[FieldSpec]) -> list[FieldSpec]:
    """``fields.yaml`` as shipped, or with the dev-only choice applied."""
    if config == "rules_first":
        return shipped
    if config != "dev_choice":
        raise ValueError(f"unknown config {config!r}")
    return [
        f.model_copy(update={"extractor": "qa_finetuned", "fallback": "rules"})
        if f.id in DEV_CHOICE_FIELDS
        else f
        for f in shipped
    ]


def score_xrays(
    xrays: dict[str, XRay], rows: list[dict[str, Any]], fields: dict[str, FieldSpec]
) -> list[dict[str, Any]]:
    """One record per gold row: did the X-Ray's chosen value match gold?"""
    out = []
    for row in rows:
        result = next(f for f in xrays[row["ipo_id"]].fields if f.field_id == row["field_id"])
        chosen = result.chosen.value if result.chosen is not None else None
        out.append(
            {
                "ipo_id": row["ipo_id"],
                "field_id": row["field_id"],
                "nvm": nvm(chosen, gold_value(row, fields[row["field_id"]])),
                "extractor": result.chosen.extractor if result.chosen else None,
                "verdict": result.verdict,
                "reason_code": result.reason_code,
            }
        )
    return out


def _per_ipo(records: list[dict[str, Any]]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = defaultdict(list)
    for r in records:
        out[r["ipo_id"]].append(float(r["nvm"]))
    return dict(out)


def _r(x: float) -> float:
    return round(x, 4)


def summarise(scored: dict[str, list[dict[str, Any]]], splits: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {"configs": {}, "paired": {}}
    for config, records in scored.items():
        entry: dict[str, Any] = {}
        for split in SPLITS:
            mine = [r for r in records if splits[r["ipo_id"]] == split]
            mean, low, high = bootstrap_ci(_per_ipo(mine))
            by_field: dict[str, list[float]] = defaultdict(list)
            for r in mine:
                by_field[r["field_id"]].append(float(r["nvm"]))
            entry[split] = {
                "n": len(mine),
                "nvm": _r(mean),
                "nvm_ci95": [_r(low), _r(high)],
                "per_field": {
                    f: {"n": len(v), "nvm": _r(sum(v) / len(v))}
                    for f, v in sorted(by_field.items())
                },
            }
        result["configs"][config] = entry
    for split in SPLITS:
        a = _per_ipo([r for r in scored["rules_first"] if splits[r["ipo_id"]] == split])
        b = _per_ipo([r for r in scored["dev_choice"] if splits[r["ipo_id"]] == split])
        diff, low, high = paired_bootstrap(a, b)
        result["paired"][f"rules_first_minus_dev_choice_{split}"] = {
            "diff": _r(diff),
            "ci95": [_r(low), _r(high)],
        }
    return result


def build(processed_dir: Path, gold: list[dict[str, Any]]) -> dict[str, Any]:
    shipped = load_fields()
    ipos = list_demo_ipos()
    splits = {i.ipo_id: i.split for i in ipos}
    rows = ladder_rows([r for r in gold if r["ipo_id"] in splits], shipped)
    docs = {i.ipo_id: {d: load_inputs(processed_dir, i.ipo_id, d) for d in ("rhp", "prospectus")}
            for i in ipos}  # fmt: skip
    scored: dict[str, list[dict[str, Any]]] = {}
    for config in CONFIGS:
        fields = config_fields(config, shipped)
        xrays = {i.ipo_id: build_xray(i.ipo_id, i.company, docs[i.ipo_id], BUILT_AT, fields)
                 for i in ipos}  # fmt: skip
        scored[config] = score_xrays(xrays, rows, {f.id: f for f in fields})
    summary = summarise(scored, splits)
    return {
        "experiment": "E2+E3",
        "name": "xray_accuracy",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": {
            "gold_version": "v1",
            "n_values": len(rows),
            "dev_choice_fields": list(DEV_CHOICE_FIELDS),
        },
        **summary,
        "records": scored,
        "notes": (
            "System accuracy: the X-Ray's chosen value per ladder field against gold, NVM. "
            "rules_first = fields.yaml as shipped (G2 decision, informed by test results); "
            "dev_choice = the dev-only choice of ADR-018 (fine-tuned model primary for fresh and "
            "total issue size). Same saved candidates for both. Clean re-check on gold v2 in P5.1."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    paths = get_settings().paths
    text = (Path(paths.gold_dir) / "gold_values.jsonl").read_text(encoding="utf-8")
    gold = [json.loads(x) for x in text.splitlines() if x.strip()]
    result = build(Path(paths.processed_dir), gold)
    for config, entry in result["configs"].items():
        for split in SPLITS:
            m = entry[split]
            print(f"{config:12} {split:5} n={m['n']:3} NVM={m['nvm']} CI={m['nvm_ci95']}")
    for name, d in result["paired"].items():
        print(f"  {name:40} diff={d['diff']:+} CI={d['ci95']}")
    out = Path(paths.eval_dir) / "xray_accuracy.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")  # fmt: skip
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
