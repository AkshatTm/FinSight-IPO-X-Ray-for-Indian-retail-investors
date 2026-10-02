"""E7: the verifier on real model answers (docs/EXECUTION_PLAN C5, P3.6).

    uv run python -m finsight.evaluate.answers --split dev --limit 20 --profile dev_light

Runs the dev (or test) questions through the chat orchestrator, the same path the API uses, and
records for each turn what happened (answered, refused, abstained, error), every number's verdict
and the answer text. ``eval_results/e7_answers.json`` has the counts; ``e7_sample.jsonl`` holds
the answers with at least one number, one per line, ready for the author to hand-check
(``reviewed_by_akshat`` is left empty and nothing here is edited afterwards).
Needs Ollama running (``ollama serve``); stop it afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from finsight.chat.orchestrator import ChatOrchestrator, Event

QUESTION_FILES = {"dev": "questions_dev.jsonl", "test": "questions_test.jsonl"}


def turn_record(question: dict[str, Any], events: Iterable[Event]) -> dict[str, Any]:
    """One row per question from its event stream."""
    outcome, answer, final = "answered", "", None
    verdicts: list[dict[str, Any]] = []
    for name, ev in events:
        if name == "guard":
            outcome = "refused"
        elif name == "abstain":
            outcome = "abstained"
        elif name == "error":
            outcome = "error"
        elif name == "answer":
            answer = ev.text  # type: ignore[attr-defined]
        elif name == "verdict":
            verdicts.append(
                {
                    "status": ev.status,  # type: ignore[attr-defined]
                    "reason_code": ev.reason_code,  # type: ignore[attr-defined]
                    "span": list(ev.answer_char_span),  # type: ignore[attr-defined]
                }
            )
        elif name == "final":
            final = ev
    return {
        "ipo_id": question["ipo_id"],
        "question": question["question"],
        "language": question.get("language", "en"),
        "answerable": question.get("answerable"),
        "answer_gold": question.get("answer_gold"),
        "outcome": outcome,
        "answer": answer,
        "verdicts": verdicts,
        "timings_ms": final.timings_ms if final else {},  # type: ignore[attr-defined]
        "reviewed_by_akshat": "",
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(v["status"] for r in rows for v in r["verdicts"])
    n_numbers = sum(statuses.values())
    answered = [r for r in rows if r["outcome"] == "answered"]
    unanswerable = [r for r in rows if r["answerable"] is False]
    return {
        "n_questions": len(rows),
        "outcomes": dict(Counter(r["outcome"] for r in rows)),
        "answers_with_numbers": sum(1 for r in answered if r["verdicts"]),
        "n_numbers": n_numbers,
        "verdicts": dict(statuses),
        "verified_share": round(statuses["verified"] / n_numbers, 4) if n_numbers else None,
        "unanswerable_n": len(unanswerable),
        "unanswerable_abstained_or_not_found": sum(
            1
            for r in unanswerable
            if r["outcome"] == "abstained" or "could not find" in r["answer"]
        ),
    }


def load_questions(gold_dir: Path, split: str, limit: int | None) -> list[dict[str, Any]]:
    path = gold_dir / QUESTION_FILES[split]
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[:limit] if limit else rows


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.evaluate.answers")
    parser.add_argument("--split", choices=sorted(QUESTION_FILES), default="dev")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--profile")
    args = parser.parse_args(argv)

    from finsight.core.config import get_settings, load_settings

    settings = load_settings(args.profile) if args.profile else get_settings()
    chat = ChatOrchestrator.from_settings(args.profile)
    rows = []
    for q in load_questions(settings.paths.data_dir / "gold", args.split, args.limit):
        rows.append(
            turn_record(q, chat.events(q["ipo_id"], q["question"], q.get("language", "en")))
        )
        print(f"{len(rows)}: {rows[-1]['outcome']} {len(rows[-1]['verdicts'])} numbers", flush=True)
    out = settings.paths.eval_dir
    out.mkdir(parents=True, exist_ok=True)
    summary = {"split": args.split, "profile": args.profile, **summarise(rows)}
    (out / "e7_answers.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    sample = [r for r in rows if r["verdicts"]]
    (out / "e7_sample.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sample), "utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
