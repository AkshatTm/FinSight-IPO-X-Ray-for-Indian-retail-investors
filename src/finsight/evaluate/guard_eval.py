"""E8, keyword row: how well does the rule-based guard separate advice from facts? (05 section 5)

    uv run python -m finsight.evaluate.guard_eval [--csv data/gold/advice_guard_set.csv]

Block rate = share of advice questions the guard blocks (PRD target 95 %); false-block rate =
share of factual questions it blocks (target at most 5 %). Wilson 95 % intervals, per language
and per kind of tricky case.

Two limits are written into the result file and the ADR, not left for the reader to find:

- The advice set (60 + 60) was drafted by Claude chat, ``label_source = ai_drafted_claude_chat``,
  and **none of its rows has been reviewed by Akshat yet**; 05 section 2 asks for a set written
  by Akshat and friends.
- The rules were written and tuned **after reading that set**, so its score is in-sample. The only
  unseen measurement is ``fresh_probes_first_run``: 85 questions written after the rules and
  scored once before any rule was changed for them.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.evaluate.metrics import wilson_interval
from finsight.guard import check_advice, check_question

LABEL_SOURCE = "ai_drafted_claude_chat"
QUESTION, LANGUAGE, ADVICE, NOTE, REVIEWED = (
    "question",
    "language",
    "is_advice (must block?)",
    "tricky_note",
    "reviewed_by_akshat (Y/edit)",
)
# First and only scoring of the unseen probes in tests/guard/test_advice.py (1 Oct 2026), before the
# rules were adjusted for the three misses (decision "I should", plural "investors", two accounts).
FRESH_PROBES_FIRST_RUN = {
    "advice_blocked": "33/36",
    "factual_false_blocks": "0/49",
    "privacy_blocked": "11/11",
    "business_contacts_false_blocks": "0/10",
    "note": "Written by Claude after the rules and before scoring; privacy probes were written "
    "knowing the rule set, so they test regressions more than generalisation.",
}


def _rate(hits: int, n: int) -> dict[str, Any]:
    low, high = wilson_interval(hits, n)
    return {"rate": round(hits / n, 4) if n else None, "hits": hits, "n": n,
            "wilson_95": [round(low, 4), round(high, 4)]}  # fmt: skip


def load_set(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    missing = {QUESTION, LANGUAGE, ADVICE} - set(rows[0] if rows else {})
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    bad = {r[ADVICE] for r in rows} - {"yes", "no"}
    if bad:
        raise ValueError(f"is_advice must be yes or no, got {sorted(bad)}")
    return rows


def run(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        result = check_question(r[QUESTION])
        out.append(
            {
                "question": r[QUESTION],
                "language": r[LANGUAGE],
                "is_advice": r[ADVICE] == "yes",
                "tricky": r.get(NOTE, ""),
                "blocked": result.blocked,
                "reason": result.reason,
                "category": result.category,
                "matched": result.matched,
            }
        )
    return out


def _split(scored: list[dict[str, Any]]) -> dict[str, Any]:
    advice = [s for s in scored if s["is_advice"]]
    factual = [s for s in scored if not s["is_advice"]]
    return {
        "block_rate": _rate(sum(s["blocked"] for s in advice), len(advice)),
        "false_block_rate": _rate(sum(s["blocked"] for s in factual), len(factual)),
    }


def summarise(scored: list[dict[str, Any]]) -> dict[str, Any]:
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_note: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in scored:
        by_language[s["language"]].append(s)
        if s["tricky"]:
            by_note[s["tricky"]].append(s)
    return {
        "overall": _split(scored),
        "by_language": {k: _split(v) for k, v in sorted(by_language.items())},
        "by_tricky_note": {
            k: {
                "n": len(v),
                "is_advice": v[0]["is_advice"],
                "correct": sum(s["blocked"] == s["is_advice"] for s in v),
            }
            for k, v in sorted(by_note.items())
        },
        "categories_blocked": dict(Counter(s["category"] for s in scored if s["blocked"])),
    }


def _git_sha() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, check=True)  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def report(rows: list[dict[str, str]], scored: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = sum(1 for r in rows if (r.get(REVIEWED) or "").strip())
    return {
        "experiment": "E8",
        "name": "guard_keyword",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "data": {
            "file": "data/gold/advice_guard_set.csv",
            "label_source": LABEL_SOURCE,
            "n_advice": sum(r[ADVICE] == "yes" for r in rows),
            "n_factual": sum(r[ADVICE] == "no" for r in rows),
            "reviewed_by_akshat": reviewed,
            "in_sample": True,
        },
        **summarise(scored),
        "fresh_probes_first_run": FRESH_PROBES_FIRST_RUN,
        "misses": [
            {k: s[k] for k in ("question", "language", "is_advice", "category", "matched")}
            for s in scored
            if s["blocked"] != s["is_advice"]
        ],
        "notes": (
            "Keyword/regex guard (ADR-046). Set drafted by Claude chat, not yet reviewed by Akshat "
            f"({reviewed}/{len(rows)} rows reviewed); rules were tuned after reading it, so these "
            "numbers are in-sample. fresh_probes_first_run is the unseen estimate. The MuRIL "
            "classifier row of E8 uses a 70/15/15 split of the same set (later)."
        ),
    }


def _line(name: str, m: dict[str, Any]) -> str:
    block, false = m["block_rate"], m["false_block_rate"]
    return (
        f"{name:9} block {block['hits']}/{block['n']} {block['wilson_95']}"
        f"  false-block {false['hits']}/{false['n']} {false['wilson_95']}"
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    paths = get_settings().paths
    parser = argparse.ArgumentParser(prog="finsight.evaluate.guard_eval")
    parser.add_argument("--csv", type=Path, default=Path(paths.gold_dir) / "advice_guard_set.csv")
    parser.add_argument("--compare", action="store_true", help="keyword vs MuRIL on the test part")
    args = parser.parse_args(argv)
    if args.compare:
        clf = json.loads((Path(paths.eval_dir) / "guard_clf.json").read_text(encoding="utf-8"))
        result = compare(clf)
        for name in ("keyword", "muril"):
            print(_line(name, result[name]["overall"]))
        out = Path(paths.eval_dir) / "guard_compare.json"
        out.write_text(
            json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {out}")
        return 0
    rows = load_set(args.csv)
    result = report(rows, run(rows))
    print(_line("overall", result["overall"]))
    for lang, m in result["by_language"].items():
        print(_line(lang, m))
    out = Path(paths.eval_dir) / "guard.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                   newline="\n")  # fmt: skip
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ----------------------------------------------------------------------------- keyword vs MuRIL
def compare(clf: dict[str, Any], threshold: float = 0.5) -> dict[str, Any]:
    """E8, classifier row: keyword rules and the MuRIL classifier on the same held-out questions.

    The test part is 15 % of the AI-drafted set (about 18 questions): the intervals are wide and
    the rules were tuned after reading the whole set (in-sample), so a tie or a small difference
    here is not evidence either way. Reported as measured, per language.
    """
    test = clf["best_seed_predictions"]["test"]
    scored = [
        r
        | {
            "is_advice": r["label"] == "advice",
            "muril": r["p_advice"] >= threshold,
            "keyword": check_advice(r["question"]).blocked,
        }
        for r in test
    ]

    def part(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
        adv = [r for r in rows if r["is_advice"]]
        fact = [r for r in rows if not r["is_advice"]]
        return {
            "block_rate": _rate(sum(r[key] for r in adv), len(adv)),
            "false_block_rate": _rate(sum(r[key] for r in fact), len(fact)),
        }

    langs = sorted({s["language"] for s in scored})
    return {
        "experiment": "E8",
        "name": "guard_compare",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "n_test": len(scored),
        "threshold": threshold,
        "best_seed": clf.get("best_seed_by_val_f1"),
        "keyword": {
            "overall": part(scored, "keyword"),
            "by_language": {
                lg: part([s for s in scored if s["language"] == lg], "keyword") for lg in langs
            },
        },
        "muril": {
            "overall": part(scored, "muril"),
            "by_language": {
                lg: part([s for s in scored if s["language"] == lg], "muril") for lg in langs
            },
        },
        "disagreements": [
            {k: s[k] for k in ("question", "language", "is_advice", "keyword", "muril", "p_advice")}
            for s in scored
            if s["keyword"] != s["muril"]
        ],
        "notes": (
            "Held-out 15 % (seed 2026 split, stratified by language and label) of the AI-drafted "
            "E8 set, not reviewed by Akshat. The keyword rules were tuned on the whole set, so "
            "their number is in-sample; MuRIL never saw these questions. The test part is tiny: "
            "read the intervals, not the point estimates."
        ),
    }
