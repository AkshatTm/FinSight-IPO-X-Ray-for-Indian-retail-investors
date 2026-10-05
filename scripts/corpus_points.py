"""Per-IPO risk-level scores and the fitted thresholds (C2.8, E17).

    uv run python scripts/corpus_points.py scores [--points-only]
    uv run python scripts/corpus_points.py fit

``scores`` reads each IPO's scored risks (``<ipo_id>.json``: Risk objects with seriousness and
novelty, written by the upload pipeline once the C2 models are wired in, C3.3) and, unless
``--points-only``, its red flags (``<ipo_id>.flags.json``); it writes ``reference_scores.csv``.
``--points-only`` is the variant for the corpus years, which have no tables and so no red flags.
``fit`` takes the bottom and top third of the **train + dev** scores (``finsight.risklevel
.reference``), writes ``eval_results/b/risklevel_fit.json`` and rewrites ``configs/risklevel.yaml``
(``provisional: false``, ``computed_on`` = the git sha). Test and bench scores are never used.

This script never reads listing outcomes: those live only in ``scripts/validate_risklevel.py``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.core.schemas import RedFlag, Risk  # noqa: E402
from finsight.risklevel import compute, load_config  # noqa: E402
from finsight.risklevel.reference import (  # noqa: E402
    apply_fit,
    fit_thresholds,
    read_scores,
    write_scores,
)
from finsight.splits import load_splits, reference_config  # noqa: E402

SCORED = ROOT / "data" / "processed" / "risk_bank" / "scored"
TABLE = ROOT / "data" / "processed" / "risk_bank" / "reference_scores.csv"
CONFIG = ROOT / "configs" / "risklevel.yaml"
FIT = ROOT / "eval_results" / "b" / "risklevel_fit.json"


def cmd_scores(points_only: bool) -> None:
    """Score every IPO of the split that has scored risks."""
    cfg = load_config()
    scores: dict[str, float] = {}
    missing = []
    for e in load_splits(ROOT / "configs" / "splits.yaml").ipos:
        risks_file = SCORED / f"{e.ipo_id}.json"
        if not risks_file.exists():
            missing.append(e.ipo_id)
            continue
        risks = [Risk.model_validate(r) for r in json.loads(risks_file.read_text(encoding="utf-8"))]
        flags_file = SCORED / f"{e.ipo_id}.flags.json"
        flags = (
            []
            if points_only or not flags_file.exists()
            else [
                RedFlag.model_validate(f)
                for f in json.loads(flags_file.read_text(encoding="utf-8")).get("flags", [])
            ]
        )
        scores[e.ipo_id] = compute(flags, risks, cfg).score
    write_scores(scores, TABLE)
    print(f"scored {len(scores)} IPOs, {len(missing)} without scored risks -> {TABLE}")


def cmd_fit() -> None:
    """Fit thresholds on train + dev and rewrite the config."""
    splits = load_splits(ROOT / "configs" / "splits.yaml")
    fit = fit_thresholds(read_scores(TABLE), splits)
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    ).stdout.strip()
    window = int(reference_config()["window_years"])
    CONFIG.write_text(apply_fit(CONFIG.read_text("utf-8"), fit, sha, window), "utf-8", newline="\n")
    FIT.parent.mkdir(parents=True, exist_ok=True)
    record = {k: v for k, v in fit.items() if k != "fit_ipos"}
    record |= {"n_fit_ipos": len(fit["fit_ipos"]), "computed_on": sha, "window_years": window,
               "fitted_on": "train + dev IPOs only"}  # fmt: skip
    FIT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record["thresholds"]), "->", CONFIG)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["scores", "fit"])
    ap.add_argument("--points-only", action="store_true")
    a = ap.parse_args(argv)
    if a.command == "scores":
        cmd_scores(a.points_only)
    else:
        cmd_fit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
