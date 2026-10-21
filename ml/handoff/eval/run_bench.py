"""Evaluate a student candidate on FinSight Bench v1 Tasks A / C (runs on the LAPTOP, not Colab).

Bench v1 is frozen and needs Ollama, so this wrapper runs in the product repo checkout (CC or
Akshat runs it; ARGON asks in ``comms/to_cc.md``). Steps for a candidate Ollama tag ``TAG``
(e.g. ``finsight-student:v2-q4``):

    1. `ollama create TAG -f Modelfile` (from the delivery's GGUF);
    2. python ml/handoff/eval/run_bench.py --product-repo <repo> --tag TAG --system student_v2

The product's ``scripts/bench_run.py`` and ``scripts/bench_score.py`` do the work; this script only
reads the scored summary and compares Task C and Task A with ``baselines.json`` (single run,
7 IPOs: differences inside the interval are ties). It never edits a result file.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def compare(summary: dict[str, Any], system: str, baselines: dict[str, Any]) -> dict[str, Any]:
    """Task C (and A) of ``system`` against the v1.0 student baseline."""
    sysm = summary["systems"][system]
    c, b = sysm["C"], baselines["m1_chat_bench_v1"]
    halluc = c["hallucinated_number_unanswerable"]["mean"]
    correct = c["correct_answerable"]["mean"]
    return {
        "system": system,
        "single_run": True,
        "hallucinated_unanswerable": {
            "new": halluc,
            "baseline": b["hallucinated_number_on_unanswerable"]["mean"],
            "target_max": b["target"]["hallucinated_max"],
            "interval": [
                c["hallucinated_number_unanswerable"]["low"],
                c["hallucinated_number_unanswerable"]["high"],
            ],
            "reaches_target": halluc <= b["target"]["hallucinated_max"],
        },
        "correct_answerable": {
            "new": correct,
            "baseline": b["correct_on_answerable"]["mean"],
            "target_min": b["target"]["correct_answerable_min"],
            "reaches_target": correct >= b["target"]["correct_answerable_min"],
        },
        "task_a_nvm": sysm["A"]["nvm"]["mean"],
        "baseline_task_a_nvm": b["student_task_a"]["nvm"]["mean"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--product-repo", type=Path, required=True)
    ap.add_argument(
        "--system", default="student", help="system name registered in scripts/bench_run.py"
    )
    ap.add_argument(
        "--tag", help="Ollama tag (CC registers it as the system's model in bench_run.py)"
    )
    ap.add_argument(
        "--skip-run", action="store_true", help="only compare an existing scored summary"
    )
    ap.add_argument("--baselines", type=Path, default=HERE / "baselines.json")
    args = ap.parse_args(argv)
    repo = args.product_repo
    if not args.skip_run:
        for script in ("bench_run.py", "bench_score.py"):
            cmd = [sys.executable, str(repo / "scripts" / script)]
            if script == "bench_run.py":
                cmd += ["--system", args.system, "--tasks", "AC"]
            subprocess.run(cmd, cwd=repo, check=True)
    summary = json.loads((repo / "eval_results" / "c4" / "bench_summary.json").read_text("utf-8"))
    baselines = json.loads(args.baselines.read_text(encoding="utf-8"))
    print(json.dumps(compare(summary, args.system, baselines), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
