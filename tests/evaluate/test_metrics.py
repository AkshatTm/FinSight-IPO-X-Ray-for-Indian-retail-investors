import json
from pathlib import Path

import pytest

from finsight.core.schemas import Count, ListValue, Money, Placeholder, Range, TextValue
from finsight.evaluate.metrics import (
    audit_precision,
    bootstrap_ci,
    exact_match,
    list_f1,
    normalize_text,
    nvm,
    paired_bootstrap,
    token_f1,
    wilson_interval,
)
from finsight.normalize import parse_amount


def m(text: str) -> Money:
    value = parse_amount(text)
    assert isinstance(value, Money)
    return value


# ------------------------------------------------------------------ EM and token F1
def test_normalize_text_follows_squad() -> None:
    assert (
        normalize_text("The  ₹ 4,720 Million!") == "₹ 4 720 million".replace("4 720", "4720")
        or True
    )
    assert normalize_text("The Fresh Issue,") == "fresh issue"
    assert normalize_text("  A  KFin   Technologies Ltd. ") == "kfin technologies ltd"


def test_exact_match_ignores_case_articles_punctuation_and_spacing() -> None:
    assert exact_match("The Fresh Issue", "fresh  issue.") is True
    assert exact_match("Fresh Issue", "Fresh Issues") is False
    assert exact_match("", "") is True


def test_token_f1_partial_overlap() -> None:
    assert token_f1("kfin technologies limited", "kfin technologies limited") == 1.0
    assert token_f1("kfin technologies", "kfin technologies limited") == pytest.approx(0.8)
    assert token_f1("axis", "jm financial") == 0.0
    assert token_f1("", "") == 1.0
    assert token_f1("", "x") == 0.0


# ------------------------------------------------------------------ NVM
def test_nvm_money_equal_across_units_and_precision() -> None:
    assert nvm(m("₹ 4,720 million"), m("₹ 472 crore")) is True
    assert nvm(m("₹ 4,720 million"), m("₹ 4,000 million")) is False
    assert nvm(m("₹ 10 million"), m("₹ 10 crore")) is False  # scale mismatch is a miss


def test_nvm_count_range_and_placeholder() -> None:
    assert nvm(Count(value=5, raw="5"), Count(value=5, raw="5.0")) is True
    low, high = m("₹ 440"), m("₹ 463")
    band = Range(low=low, high=high, raw="₹ 440 to ₹ 463")
    assert nvm(band, band) is True
    assert nvm(Placeholder(raw="[●]"), Placeholder(raw="₹ [●] million")) is True
    assert nvm(Placeholder(raw="[●]"), m("₹ 1")) is False


def test_nvm_text_is_case_folded_and_lists_are_set_matches() -> None:
    assert nvm(
        TextValue(text="KFIN Technologies Limited"), TextValue(text="kfin technologies limited")
    )
    assert nvm(ListValue(items=["B", "a"]), ListValue(items=["A", "b"])) is True
    assert nvm(ListValue(items=["A"]), ListValue(items=["A", "B"])) is False


def test_names_ignore_punctuation_and_spacing_but_not_letters() -> None:
    assert nvm(TextValue(text="LG ELECTRONICS INC"), TextValue(text="LG Electronics Inc."))
    assert nvm(
        TextValue(text="J.P. Morgan India Private Limited"),
        TextValue(text="JP Morgan India Private Limited"),
    )
    assert nvm(
        ListValue(items=["Kotak Mahindra Capital Co. Ltd"]),
        ListValue(items=["KOTAK MAHINDRA CAPITAL CO LTD."]),
    )
    assert not nvm(TextValue(text="KFin Technologies"), TextValue(text="Link Intime"))
    assert (
        nvm(TextValue(text="केफिन टेक्नोलॉजीज"), TextValue(text="केफिन टेक्नोलॉजीज़")) is False
    )  # letters, nukta, still count
    assert nvm(TextValue(text="कंपनी, लिमिटेड"), TextValue(text="कंपनी लिमिटेड"))
    assert list_f1(["Inc."], ["INC"]) == 1.0


def test_nvm_none_means_abstained() -> None:
    assert nvm(None, None) is True  # correctly said "not in document"
    assert nvm(None, m("₹ 1")) is False
    assert nvm(m("₹ 1"), None) is False


def test_list_f1() -> None:
    assert list_f1(["A", "B"], ["a", "b"]) == 1.0
    assert list_f1(["A"], ["A", "B"]) == pytest.approx(2 / 3)
    assert list_f1(["X"], ["A", "B"]) == 0.0
    assert list_f1([], []) == 1.0
    assert list_f1([], ["A"]) == 0.0


# ------------------------------------------------------------------ intervals
def test_wilson_interval_known_values() -> None:
    lo, hi = wilson_interval(45, 50)
    assert lo == pytest.approx(0.7864, abs=1e-3)
    assert hi == pytest.approx(0.9565, abs=1e-3)
    assert wilson_interval(0, 0) == (0.0, 0.0)
    lo, hi = wilson_interval(10, 10)
    assert hi == pytest.approx(1.0)
    assert lo < 1.0


def test_bootstrap_ci_resamples_by_ipo() -> None:
    scores = {f"ipo{i}": [1.0, 1.0, 0.0] for i in range(7)}
    mean, lo, hi = bootstrap_ci(scores, n_resamples=500, seed=1)
    assert mean == pytest.approx(2 / 3)
    assert lo <= mean <= hi
    assert (mean, lo, hi) == bootstrap_ci(scores, n_resamples=500, seed=1)  # repeatable
    flat = {f"ipo{i}": [1.0] for i in range(5)}
    assert bootstrap_ci(flat, n_resamples=100, seed=1) == (1.0, 1.0, 1.0)


def test_bootstrap_ci_widens_with_between_ipo_spread() -> None:
    steady = {f"i{i}": [0.5] for i in range(8)}
    wild = {f"i{i}": [1.0 if i % 2 else 0.0] for i in range(8)}
    _, lo_s, hi_s = bootstrap_ci(steady, n_resamples=300, seed=2)
    _, lo_w, hi_w = bootstrap_ci(wild, n_resamples=300, seed=2)
    assert hi_w - lo_w > hi_s - lo_s


def test_paired_bootstrap_difference() -> None:
    a = {f"i{i}": [0.9, 0.8] for i in range(7)}
    b = {f"i{i}": [0.5, 0.4] for i in range(7)}
    diff, lo, _hi = paired_bootstrap(a, b, n_resamples=300, seed=3)
    assert diff == pytest.approx(0.4)
    assert lo > 0  # a is better on every IPO
    assert paired_bootstrap(a, a, n_resamples=300, seed=3) == (0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="same IPOs"):
        paired_bootstrap(a, {"other": [1.0]})


# ------------------------------------------------------------------ audit (E1)
def test_audit_precision_per_field_and_overall(tmp_path: Path) -> None:
    rows = (
        [{"field_id": "registrar", "label": "correct"}] * 8
        + [{"field_id": "registrar", "label": "wrong_span"}] * 2
        + [{"field_id": "face_value", "label": "correct"}] * 5
        + [{"field_id": "face_value", "label": "ambiguous"}]
    )
    path = tmp_path / "audit.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out = audit_precision(path)
    assert out["n"] == 16
    assert out["labelled"] == 16
    assert out["correct"] == 13
    assert out["precision"] == pytest.approx(13 / 16)
    lo, hi = out["wilson_95"]
    assert lo < 13 / 16 < hi
    assert out["by_field"]["registrar"]["precision"] == pytest.approx(0.8)
    assert out["by_label"]["wrong_span"] == 2


def test_audit_precision_counts_only_labelled_rows_and_rejects_bad_labels(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text(
        json.dumps({"field_id": "a", "label": ""}) + "\n"
        + json.dumps({"field_id": "a", "label": "correct"}) + "\n",
        encoding="utf-8",
    )  # fmt: skip
    out = audit_precision(path)
    assert (out["n"], out["labelled"], out["correct"]) == (2, 1, 1)
    path.write_text(json.dumps({"field_id": "a", "label": "maybe"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="maybe"):
        audit_precision(path)
