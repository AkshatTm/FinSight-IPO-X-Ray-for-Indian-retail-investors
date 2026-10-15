"""E15 scorer (``scripts/redflag_eval.py``): row scoring, summary and the C-ADR-02 gates."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from finsight.core.config import project_root

SPEC = importlib.util.spec_from_file_location(
    "redflag_eval", project_root() / "scripts" / "redflag_eval.py"
)
assert SPEC is not None
assert SPEC.loader is not None
ev = importlib.util.module_from_spec(SPEC)
sys.modules["redflag_eval"] = ev
SPEC.loader.exec_module(ev)

GOLD = [
    {"ipo_id": "a", "rf": "RF01", "status": "ok"},
    {"ipo_id": "a", "rf": "RF02", "status": "concern"},
    {"ipo_id": "a", "rf": "RF03", "status": "not_available"},
    {"ipo_id": "a", "rf": "RF04", "status": "watch"},
]


def test_rows_are_scored_and_serious_disagreements_counted() -> None:
    pred = {"a": {"RF01": "concern", "RF02": "concern", "RF03": "not_available", "RF04": "ok"}}
    rows = ev.score_rows(GOLD, pred)
    assert [r["correct"] for r in rows] == [False, True, True, False]
    assert [r["serious"] for r in rows] == [True, False, False, False]  # ok vs concern only


def test_a_missing_ipo_scores_wrong_not_crashes() -> None:
    rows = ev.score_rows(GOLD, {})
    assert {r["pred"] for r in rows} == {"missing"}
    assert not any(r["correct"] for r in rows)


def test_summary_accuracy_confusion_and_per_check() -> None:
    pred = {"a": {"RF01": "ok", "RF02": "watch", "RF03": "not_available", "RF04": "watch"}}
    s = ev.summarise(ev.score_rows(GOLD, pred))
    assert s["accuracy"] == 0.75
    assert s["n_valued"] == 3
    assert s["accuracy_on_valued_gold"] == pytest.approx(0.667, abs=0.001)
    assert s["confusion"]["concern"] == {"watch": 1}
    assert s["per_check"]["RF02"] == {"n": 1, "accuracy": 0.0}
    assert s["serious_disagreements"] == 0


def test_non_dev_slices_need_final_and_a_verified_gold(tmp_path: Path) -> None:
    gold = tmp_path / "g.jsonl"
    gold.write_text(json.dumps(GOLD[0] | {"label_source": "computed_from_gold_v3"}) + "\n")
    with pytest.raises(SystemExit):
        ev.main(["--slice", "test", "--gold", str(gold)])  # test slice without --final
    with pytest.raises(SystemExit):
        ev.main(["--slice", "all", "--final", "--allow-unverified", "--gold", str(gold)])
    with pytest.raises(SystemExit):
        ev.main(["--gold", str(tmp_path / "missing.jsonl")])
