"""E21: does the risk-points-only score relate to listing outcomes? (C2.8)

    uv run python scripts/validate_risklevel.py --outcomes data/gold/outcomes.csv

``outcomes.csv`` has ``ipo_id,listing_gain_pct``. Reads the score table written by
``scripts/corpus_points.py scores --points-only`` and the fitted thresholds in
``configs/risklevel.yaml``; writes ``eval_results/b/risklevel_validation.json`` with the
limitation stated. Evaluation only: nothing here feeds a threshold, a prompt or the product, and
the result is reported whatever it shows. No investment advice.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.evaluate.outcomes import validate  # noqa: E402
from finsight.risklevel import load_config  # noqa: E402
from finsight.risklevel.reference import read_scores  # noqa: E402

TABLE = ROOT / "data" / "processed" / "risk_bank" / "reference_scores.csv"
RESULT = ROOT / "eval_results" / "b" / "risklevel_validation.json"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outcomes", type=Path, required=True)
    ap.add_argument("--column", default="listing_gain_pct")
    a = ap.parse_args(argv)
    with a.outcomes.open(encoding="utf-8", newline="") as fh:
        outcomes = {r["ipo_id"]: float(r[a.column]) for r in csv.DictReader(fh) if r.get(a.column)}
    cfg = load_config()
    if cfg.get("provisional"):
        sys.exit("risklevel.yaml is still provisional: run corpus_points.py fit first")
    result = validate(read_scores(TABLE), outcomes, cfg["thresholds"], a.column)
    result["label_source"] = "measured outcomes; scores from the pipeline (AI-assisted risk labels)"
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("n", "spearman_rho", "permutation_p")}), "->", RESULT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
