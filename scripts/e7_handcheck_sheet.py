"""Hand-check sheet for the E7 samples (C3.7): ``data/gold/e7_handcheck.csv``.

    uv run python scripts/e7_handcheck_sheet.py

One row per sampled answer (20 dev + 20 test, ``eval_results/e7_sample_*.jsonl``), with the gold
answer, the system's answer, the verifier's tick counts and one short instruction. Rows whose
verifier marked a number contradicted come first. Akshat fills the last two columns; nothing
is read back automatically.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "gold" / "e7_handcheck.csv"

INSTRUCTION = (
    "Is the answer right against the gold? Then check each number the verifier ticked "
    "(✅ verified / ⚠️ unverifiable / ❌ contradicted): was the tick fair? Fill the last 2 columns."
)


def _ticks(verdicts: list[dict[str, Any]]) -> str:
    c = Counter(str(v.get("status")) for v in verdicts)
    return f"✅{c['verified']} ⚠️{c['unverifiable']} ❌{c['contradicted']}"


def sheet_rows(samples: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Sheet rows, contradicted numbers first, then unverifiable, then the rest."""
    rows = []
    for sl, items in samples.items():
        for i, r in enumerate(items, 1):
            v = r.get("verdicts") or []
            bad = sum(x.get("status") == "contradicted" for x in v)
            soft = sum(x.get("status") == "unverifiable" for x in v)
            rows.append(
                {
                    "id": f"{sl}-{i:02d}", "slice": sl, "ipo": r["ipo_id"],
                    "language": r["language"], "question": r["question"],
                    "answerable_in_document": "yes" if r["answerable"] else "no",
                    "gold_answer": r["answer_gold"], "system_answer": r["answer"],
                    "number_ticks": _ticks(v), "instruction": INSTRUCTION,
                    "answer_right_yes_no": "", "ticks_fair_yes_no_or_note": "",
                    "_sort": (-bad, -soft, sl, i),
                }
            )  # fmt: skip
    rows.sort(key=lambda r: r["_sort"])
    for r in rows:
        del r["_sort"]
    return rows


def main() -> int:
    """Write the sheet."""
    samples = {
        sl: [
            json.loads(x)
            for x in (ROOT / "eval_results" / f"e7_sample_{sl}.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if x.strip()
        ]
        for sl in ("dev", "test")
    }
    rows = sheet_rows(samples)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
