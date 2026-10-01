"""X-Ray accuracy under two extractor configurations, from made-up candidates."""

from datetime import UTC, datetime
from typing import Any

import pytest

from finsight.core.schemas import Candidate
from finsight.evaluate.xray_accuracy import config_fields, score_xrays, summarise
from finsight.extract import DocInputs, build_xray, load_fields
from finsight.normalize import parse_amount

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def cand(extractor: str, raw: str, score: float = 0.9) -> Candidate:
    return Candidate(field_id="fresh_issue_size", extractor=extractor, doc_type="rhp", raw=raw,
                     value=parse_amount(raw), page=1, score=score)  # fmt: skip


def gold_row(ipo: str, value: str) -> dict[str, Any]:
    return {"ipo_id": ipo, "field_id": "fresh_issue_size", "doc": "rhp", "value_raw": value,
            "status": "present"}  # fmt: skip


def test_dev_choice_puts_the_model_first_for_two_fields_only() -> None:
    shipped = load_fields()
    fields = {f.id: f for f in config_fields("dev_choice", shipped)}
    assert (fields["fresh_issue_size"].extractor, fields["fresh_issue_size"].fallback) == (
        "qa_finetuned",
        "rules",
    )
    assert fields["total_issue_size"].extractor == "qa_finetuned"
    assert fields["registrar"].extractor == "rules"
    assert config_fields("rules_first", shipped) is shipped
    with pytest.raises(ValueError, match="unknown config"):
        config_fields("nope", shipped)


def test_the_chosen_value_is_scored_against_gold_and_the_configs_differ_where_they_disagree() -> (
    None
):
    shipped = load_fields()
    fields = {f.id: f for f in shipped}
    rows = [gold_row("a", "₹ 100 million"), gold_row("b", "₹ 200 million")]
    # a: rules right, model wrong; b: rules wrong, model right
    candidates = {"a": ("₹ 100 million", "₹ 150 million"), "b": ("₹ 250 million", "₹ 200 million")}
    scored = {}
    for config in ("rules_first", "dev_choice"):
        spec = config_fields(config, shipped)
        xrays = {}
        for i, (r, m) in candidates.items():
            both = {"fresh_issue_size": [cand("rules", r), cand("qa_finetuned", m)]}
            docs = {"rhp": DocInputs(candidates=both), "prospectus": DocInputs()}
            xrays[i] = build_xray(i, i, docs, NOW, spec)
        scored[config] = score_xrays(xrays, rows, fields)
    assert [r["nvm"] for r in scored["rules_first"]] == [True, False]
    assert [r["nvm"] for r in scored["dev_choice"]] == [False, True]
    assert [r["extractor"] for r in scored["rules_first"]] == ["rules", "rules"]
    assert [r["extractor"] for r in scored["dev_choice"]] == ["qa_finetuned", "qa_finetuned"]
    assert all(r["verdict"] == "unverifiable" for r in scored["rules_first"])  # they disagree


def test_summary_has_both_splits_intervals_and_the_paired_difference() -> None:
    def rec(ipo: str, ok: bool) -> dict[str, Any]:
        return {"ipo_id": ipo, "field_id": "fresh_issue_size", "nvm": ok}

    splits = {"d1": "dev", "t1": "test", "t2": "test", "t3": "test"}
    rules_first = [rec("d1", True), rec("t1", True), rec("t2", True), rec("t3", False)]
    dev_choice = [rec("d1", True), rec("t1", True), rec("t2", False), rec("t3", False)]
    s = summarise({"rules_first": rules_first, "dev_choice": dev_choice}, splits)
    test = s["configs"]["rules_first"]["test"]
    assert test["n"] == 3
    assert test["nvm"] == pytest.approx(2 / 3, abs=1e-4)
    assert test["nvm_ci95"][0] <= test["nvm"] <= test["nvm_ci95"][1]
    assert s["configs"]["dev_choice"]["test"]["per_field"]["fresh_issue_size"] == {
        "n": 3,
        "nvm": pytest.approx(1 / 3, abs=1e-4),
    }
    paired = s["paired"]["rules_first_minus_dev_choice_test"]
    assert paired["diff"] == pytest.approx(1 / 3, abs=1e-4)
    assert s["paired"]["rules_first_minus_dev_choice_dev"]["diff"] == 0.0
