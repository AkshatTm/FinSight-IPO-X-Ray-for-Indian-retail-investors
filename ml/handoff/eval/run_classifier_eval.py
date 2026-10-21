"""Score classifier prediction files with the product's exact metrics (3-seed mean and std).

Runs anywhere (stdlib + the bundled ``vendor/finsight_lite``; no product import):

    python run_classifier_eval.py --task band --pred dev-predictions-band-13.json
        dev-predictions-band-42.json dev-predictions-band-2026.json   (one command, wrapped)
    python run_classifier_eval.py --task category --pred dev-predictions-13.json ...

A prediction file is a JSON list of ``{"risk_id", "gold", "pred", "probs"}``; ``gold``/``pred`` are
band numbers ("1".."4", 4 = severe) or category names. Output: per-seed metrics, mean and std,
and the comparison with ``baselines.json`` (BEATS / TIES / LOSES on the primary metric; a model
that loses is reported as LOSES, not hidden). Single seeds are labelled as such.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))

from finsight_lite.clf_metrics import band_scores, scores  # noqa: E402

TIE_BAND = 0.02  # recall differences inside +-0.02 are a tie (about one severe row of 58)
TIE_F1 = 0.005


def _load(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_file(task: str, path: Path) -> dict[str, Any]:
    """Metrics for one prediction file."""
    rows = _load(path)
    if task == "band":
        gold = [int(r["gold"]) for r in rows]
        pred = [int(r["pred"]) for r in rows]
        m = band_scores(gold, pred)
        return {
            k: m[k]
            for k in ("n", "mae", "severe_recall", "severe_precision", "severe_support", "macro_f1")
        }
    labels = sorted({r["gold"] for r in rows} | {r["pred"] for r in rows})
    m = scores([r["gold"] for r in rows], [r["pred"] for r in rows], labels)
    return {"n": len(rows), "macro_f1": m["macro_f1"], "accuracy": m["accuracy"]}


def aggregate(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean and std of every numeric metric over seeds."""
    out: dict[str, Any] = {"n_seeds": len(per_seed)}
    for key in per_seed[0]:
        vals = [float(s[key]) for s in per_seed if s.get(key) is not None]
        if vals:
            out[key] = {
                "mean": round(statistics.fmean(vals), 4),
                "std": round(statistics.stdev(vals), 4) if len(vals) > 1 else None,
            }
    return out


def verdict(value: float, baseline: float, tie: float) -> str:
    """BEATS / TIES / LOSES against a baseline with a tie band."""
    if value > baseline + tie:
        return "BEATS"
    if value < baseline - tie:
        return "LOSES"
    return "TIES"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--task", choices=["band", "category"], required=True)
    ap.add_argument("--pred", type=Path, nargs="+", required=True)
    ap.add_argument("--baselines", type=Path, default=HERE / "baselines.json")
    args = ap.parse_args(argv)
    per_seed = [score_file(args.task, p) for p in args.pred]
    agg = aggregate(per_seed)
    base = json.loads(args.baselines.read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "task": args.task,
        "files": [str(p) for p in args.pred],
        "per_seed": per_seed,
        "aggregate": agg,
    }
    if args.task == "band":
        b = base["m4_severity"]
        result["baseline_severe_recall"] = b["severe_recall_mean"]
        result["verdict_severe_recall"] = verdict(
            agg["severe_recall"]["mean"], b["severe_recall_mean"], TIE_BAND
        )
        result["reaches_target_0.70"] = (
            agg["severe_recall"]["mean"] >= b["target"]["severe_recall_min"]
        )
    else:
        g = base["guardrail_category"]
        drop = g["dev_macro_f1_mean"] - agg["macro_f1"]["mean"]
        result["baseline_macro_f1"] = g["dev_macro_f1_mean"]
        result["guardrail_ok"] = drop <= g["max_drop"]
        result["verdict_macro_f1"] = verdict(
            agg["macro_f1"]["mean"], g["dev_macro_f1_mean"], TIE_F1
        )
    if len(args.pred) < 3:
        result["warning"] = "fewer than 3 seeds: single-seed numbers must be labelled as such"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
