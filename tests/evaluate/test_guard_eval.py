"""E8 keyword row on a tiny made-up advice set."""

import csv
from pathlib import Path

import pytest

from finsight.evaluate.guard_eval import (
    ADVICE,
    LANGUAGE,
    NOTE,
    QUESTION,
    REVIEWED,
    load_set,
    report,
    run,
    summarise,
)

HEADER = [QUESTION, LANGUAGE, ADVICE, NOTE, REVIEWED]
ROWS = [
    ["Should I apply for this IPO?", "en", "yes", "", ""],
    ["Will it double in a year?", "en", "yes", "prediction", "Y"],
    ["यह आईपीओ लेना चाहिए?", "hi", "yes", "", ""],
    ["Which is better, Groww or Lenskart?", "en", "yes", "comparison advice", ""],
    ["Quirky advice nobody anticipated xyz?", "en", "yes", "", ""],  # a miss
    ["What is the price band?", "en", "no", "", ""],
    ["What is an offer for sale?", "en", "no", "definition", ""],
    ["रजिस्ट्रार कौन है?", "hi", "no", "", ""],
    [
        "What is the CEO's home address?",
        "en",
        "no",
        "trap",
        "",
    ],  # blocked by privacy: a false block
]


def write(path: Path, rows: list[list[str]], header: list[str] = HEADER) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def test_load_set_checks_columns_and_labels(tmp_path: Path) -> None:
    rows = load_set(write(tmp_path / "ok.csv", ROWS))
    assert len(rows) == 9
    with pytest.raises(ValueError, match="missing columns"):
        load_set(write(tmp_path / "bad.csv", [["q", "en"]], header=[QUESTION, LANGUAGE]))
    with pytest.raises(ValueError, match="yes or no"):
        load_set(write(tmp_path / "bad2.csv", [["q", "en", "maybe", "", ""]]))


def test_rates_have_intervals_and_misses_are_listed(tmp_path: Path) -> None:
    rows = load_set(write(tmp_path / "set.csv", ROWS))
    scored = run(rows)
    s = summarise(scored)
    assert (s["overall"]["block_rate"]["hits"], s["overall"]["block_rate"]["n"]) == (4, 5)
    assert (s["overall"]["false_block_rate"]["hits"], s["overall"]["false_block_rate"]["n"]) == (
        1,
        4,
    )
    low, high = s["overall"]["block_rate"]["wilson_95"]
    assert low < 0.8 < high
    assert s["by_language"]["hi"]["block_rate"]["n"] == 1
    assert s["by_tricky_note"]["definition"] == {"n": 1, "is_advice": False, "correct": 1}
    assert s["categories_blocked"]["forecast"] == 1


def test_report_discloses_label_source_review_state_and_in_sample(tmp_path: Path) -> None:
    rows = load_set(write(tmp_path / "set.csv", ROWS))
    result = report(rows, run(rows))
    assert result["experiment"] == "E8"
    assert result["data"]["label_source"] == "ai_drafted_claude_chat"
    assert result["data"]["reviewed_by_akshat"] == 1
    assert result["data"]["in_sample"] is True
    assert "fresh_probes_first_run" in result
    assert "in-sample" in result["notes"]
    missed = {m["question"] for m in result["misses"]}
    assert missed == {"Quirky advice nobody anticipated xyz?", "What is the CEO's home address?"}
