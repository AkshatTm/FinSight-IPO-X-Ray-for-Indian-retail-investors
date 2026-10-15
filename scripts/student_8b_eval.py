"""C2.5: the 8B student on gold-50 with the product post-checks, next to the 4B.

    uv run python scripts/student_8b_eval.py --model finsight-student8b:q4

Same prompt, cleaning and post-checks as the product (``Simplifier.draft``). Rewrites go to
``data/processed/gold_eval/8b/`` (not next to the rated sheet's inputs, so ``sheet50`` never picks
them up); the 4B numbers come from ``eval_results/c/student_vs_base_gold50.json``. Automated
checks only: the human gold-50 ratings stay as they are (no new sheet). Test slice, nothing here
trains or tunes anything (C-ADR-02); single seed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import gold_sets  # noqa: E402

from finsight.generate import LLMUnavailable  # noqa: E402
from finsight.risks.readability import fkgl  # noqa: E402
from finsight.risks.simplify import Simplifier, _backend  # noqa: E402

OUT_DIR = ROOT / "data" / "processed" / "gold_eval" / "8b"
RESULT = ROOT / "eval_results" / "c" / "student_8b_vs_4b_gold50.json"


def _longest(text: str) -> int:
    return max((len(s.split()) for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s), default=0)


def main() -> None:
    """Generate the 50 rewrites, post-check them and write the comparison."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="finsight-student8b:q4")
    a = ap.parse_args()
    risks = gold_sets._load(gold_sets.SET50)
    simp = Simplifier(_backend("ollama", a.model, ROOT / "models"), a.model)
    rows, secs = [], []
    for c in risks:
        text, check = "", "unavailable"
        t0 = time.perf_counter()
        for _ in range(2):
            try:
                text, check = simp.draft(c.title, c.body)
                break
            except LLMUnavailable as err:
                print(c.risk_id, "unavailable:", str(err)[:80], flush=True)
        secs.append(time.perf_counter() - t0)
        rows.append({"risk_id": c.risk_id, "model": a.model, "text": text, "check": check})
        print(c.risk_id, check or "passed", round(secs[-1], 1), flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "rewrites_student8b.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    words = [len(r["text"].split()) for r in rows]
    by_id = {c.risk_id: c for c in risks}
    summary = {
        "model": a.model,
        "pass_rate": round(sum(1 for r in rows if not r["check"]) / len(rows), 3),
        "passed": sum(1 for r in rows if not r["check"]),
        "failure_reasons": dict(Counter(r["check"].split(":")[0] for r in rows if r["check"])),
        "mean_words": round(mean(words), 1),
        "over_60_words": sum(1 for w in words if w > 60),
        "mean_longest_sentence_words": round(mean(_longest(r["text"]) for r in rows), 1),
        "fkgl_rewrite": round(mean(fkgl(r["text"]) for r in rows), 2),
        "fkgl_original": round(
            mean(fkgl(f"{by_id[r['risk_id']].title}\n\n{by_id[r['risk_id']].body}") for r in rows),
            2,
        ),
        "seconds_per_risk_gpu_offload": round(mean(secs), 1),
    }
    four = json.loads((ROOT / "eval_results/c/student_vs_base_gold50.json").read_text("utf-8"))
    out = {
        "n": len(rows),
        "split": "test (gold-50)",
        "seed": 2026,
        "systems": {"student_4b": four["systems"]["student"], "student_8b": summary},
        "note": "automated post-checks only; human ratings exist for the 4B, base and teacher",
        "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    RESULT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
