"""Base vs student on the gold-50 (test slice): product post-check pass rate and length (C2.5).

    uv run python scripts/student_vs_base.py     # -> eval_results/c/student_vs_base_gold50.json

Automated checks only (the same ``post_check`` the product uses); the human faithful / plain-English
ratings come from ``gold_sets.py sheet50`` / ``score50``. Single seed, 50 risks, test slice: nothing
here trains or tunes anything (C-ADR-02).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import gold_sets  # noqa: E402


def _words(text: str) -> int:
    return len(text.split())


def _longest_sentence(text: str) -> int:
    return max((_words(s) for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s), default=0)


def main() -> None:
    """Score both systems with the product post-check and write the summary."""
    risks = {c.risk_id: c for c in gold_sets._load(gold_sets.SET50)}
    result: dict[str, object] = {
        "n": len(risks),
        "split": "test (gold-50)",
        "seed": 2026,
        "systems": {},
    }
    for system in ("base", "student"):
        rows = [
            json.loads(line)
            for line in (gold_sets.DIR / f"rewrites_{system}.jsonl").open(encoding="utf-8")
        ]
        checks = [
            gold_sets._check(risks[r["risk_id"]], r["text"]) if r["text"] else "empty" for r in rows
        ]
        words = [_words(r["text"]) for r in rows]
        longest = [_longest_sentence(r["text"]) for r in rows]
        result["systems"][system] = {  # type: ignore[index]
            "model": rows[0]["model"],
            "pass_rate": round(sum(1 for c in checks if not c) / len(rows), 3),
            "passed": sum(1 for c in checks if not c),
            "failure_reasons": dict(Counter(c.split(":")[0][:60] for c in checks if c)),
            "mean_words": round(mean(words), 1),
            "over_60_words": sum(1 for w in words if w > 60),
            "mean_longest_sentence_words": round(mean(longest), 1),
        }
    result["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    out = ROOT / "eval_results" / "c" / "student_vs_base_gold50.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
