"""C2.5 student: CPU seconds per risk, E19 (readability) and E20 (number / certainty checks).

    uv run python scripts/student_eval.py --n-dev 60     # -> eval_results/c/student_eval.json

* CPU timing: ``finsight-student:q4`` through Ollama with ``num_gpu=0`` (no GPU layers), seconds per
  risk and generated tokens per second, on a seeded sample of dev rows (rows the student was
  monitored on, never trained on; never the test slice, C-ADR-02).
* E19: FKGL / Flesch of original vs rewrite, on those dev rows and on the gold-50 student rewrites.
* E20: the product ``post_check`` over every rewrite, rejection reasons counted.
E18 (human meaning rating) comes from ``gold_sets.py score50`` once the sheet is rated.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import gold_sets  # noqa: E402

from finsight.risks.readability import fkgl, flesch_reading_ease  # noqa: E402
from finsight.risks.simplify import MAX_NEW_TOKENS, clean, post_check  # noqa: E402

MARK = "Risk factor:\n"
DEV = ROOT / "data" / "processed" / "kaggle" / "simplify" / "dev.jsonl"
OLLAMA = "http://localhost:11434/api/chat"


def _generate(model: str, prompt: str, num_gpu: int) -> tuple[str, float, int]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": MAX_NEW_TOKENS, "num_ctx": 2048,
                    "num_gpu": num_gpu},
    }  # fmt: skip
    req = urllib.request.Request(
        OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    r = json.load(urllib.request.urlopen(req, timeout=600))
    return r["message"]["content"], r["total_duration"] / 1e9, r["eval_count"]


def _stats(pairs: list[tuple[str, str]]) -> dict[str, float]:
    orig = [fkgl(o) for o, _ in pairs]
    new = [fkgl(r) for _, r in pairs]
    return {
        "n": len(pairs),
        "fkgl_original": round(mean(orig), 2),
        "fkgl_rewrite": round(mean(new), 2),
        "fkgl_drop": round(mean(orig) - mean(new), 2),
        "flesch_original": round(mean(flesch_reading_ease(o) for o, _ in pairs), 1),
        "flesch_rewrite": round(mean(flesch_reading_ease(r) for _, r in pairs), 1),
    }


def _checks(pairs: list[tuple[str, str]]) -> dict[str, object]:
    res = [post_check(o, r) for o, r in pairs]
    return {
        "n": len(pairs),
        "rejected": sum(1 for x in res if x),
        "pass_rate": round(sum(1 for x in res if not x) / len(pairs), 3),
        "reasons": dict(Counter(x[0] for x in res if x)),
    }


def main() -> None:
    """Run the CPU sample, then score it and the gold-50 student rewrites."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-dev", type=int, default=60)
    ap.add_argument("--model", default="finsight-student:q4")
    ap.add_argument("--num-gpu", type=int, default=0, help="0 = CPU only")
    a = ap.parse_args()

    rows = [json.loads(line) for line in DEV.open(encoding="utf-8")]
    sample = random.Random(2026).sample(rows, min(a.n_dev, len(rows)))
    _generate(a.model, "Say OK.", a.num_gpu)  # load the model before timing
    dev_pairs, secs, toks = [], [], []
    for i, row in enumerate(sample, 1):
        prompt = row["messages"][0]["content"]
        original = prompt.split(MARK, 1)[1]
        raw, s, n = _generate(a.model, prompt, a.num_gpu)
        dev_pairs.append((original, clean(raw)))
        secs.append(s)
        toks.append(n)
        print(f"{i}/{len(sample)} {s:.1f}s {n} tok", flush=True)

    risks = {c.risk_id: c for c in gold_sets._load(gold_sets.SET50)}
    gold_pairs = []
    for line in (gold_sets.DIR / "rewrites_student.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        c = risks[r["risk_id"]]
        gold_pairs.append((f"{c.title}\n\n{c.body}", r["text"]))

    out = {
        "model": a.model,
        "seed": 2026,
        "cpu": {
            "num_gpu": a.num_gpu,
            "n": len(secs),
            "seconds_per_risk_mean": round(mean(secs), 1),
            "seconds_per_risk_median": round(median(secs), 1),
            "seconds_per_risk_max": round(max(secs), 1),
            "tokens_per_s": round(sum(toks) / sum(secs), 1),
            "mean_output_tokens": round(mean(toks), 1),
        },
        "e19_readability": {"dev_sample": _stats(dev_pairs), "gold50": _stats(gold_pairs)},
        "e20_checks": {"dev_sample": _checks(dev_pairs), "gold50": _checks(gold_pairs)},
        "finished_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path = ROOT / "eval_results" / "c" / "student_eval.json"
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
