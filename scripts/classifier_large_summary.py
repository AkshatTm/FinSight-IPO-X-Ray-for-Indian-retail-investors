"""C2.4: DeBERTa-v3-large (3 seeds, Colab G4) against the base model, on dev.

    uv run python scripts/classifier_large_summary.py   # -> eval_results/c/classifier_large.json

Reads the metrics pulled by ``gpu_jobs.py pull classifier_large`` (``models/risk_classifier_large``)
and the base result ``eval_results/b/classifier_base.json``. Large replaces the base only when its
dev mean beats the base mean by more than the larger seed spread; gold-150 never decides.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.risks.clf_runs import summarise, summarise_band  # noqa: E402

LARGE = ROOT / "models" / "risk_classifier_large"
BASE = ROOT / "eval_results" / "b" / "classifier_base.json"
TFIDF = ROOT / "eval_results" / "b" / "classifier_tfidf.json"
OUT = ROOT / "eval_results" / "c" / "classifier_large.json"


def main() -> None:
    """Summarise the large runs and write the comparison with the base model."""
    metrics = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(LARGE.glob("metrics-*.json"))
    ]
    tfidf = json.loads(TFIDF.read_text(encoding="utf-8")) if TFIDF.exists() else None
    cat = summarise(metrics, tfidf)
    band = summarise_band(metrics)
    base = json.loads(BASE.read_text(encoding="utf-8"))
    bcat = base.get("category", base)
    margin = max(cat["dev_macro_f1_sd"] or 0.0, bcat["dev_macro_f1_sd"] or 0.0)
    diff = cat["dev_macro_f1_mean"] - bcat["dev_macro_f1_mean"]
    out = {
        "category": cat,
        "seriousness": band,
        "vs_base": {
            "base_dev_macro_f1_mean": bcat["dev_macro_f1_mean"],
            "large_dev_macro_f1_mean": cat["dev_macro_f1_mean"],
            "difference": round(diff, 4),
            "seed_spread_used": round(margin, 4),
            "large_wins": diff > margin,
            "rule": "large replaces the base only if the dev mean gain exceeds the larger seed sd",
        },
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["vs_base"], indent=1))
    print("large category dev by seed:", cat["dev_macro_f1_by_seed"], "sd", cat["dev_macro_f1_sd"])
    print("large band dev mean:", band["dev_mean"])
    print("large gold-150 category mean:", cat.get("test_macro_f1_mean"))
    print("large gold-150 band best:", band.get("test_best_seed"))


if __name__ == "__main__":
    main()
