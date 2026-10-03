import json

import pytest

from finsight.risks import (
    CATEGORIES,
    OUTPUT_SCHEMA,
    ParseError,
    TeacherItem,
    certainty_changed,
    check_one,
    filter_outputs,
    messages,
    parse_output,
    unmatched_numbers,
    word_count,
)
from finsight.risks.filters import MAX_WORDS, REASONS

ORIGINAL = (
    "Title: We depend on a few customers\n\n"
    "Our top ten customers contributed 62.48% of our revenue from operations in Fiscal 2024. "
    "The loss of any of them may adversely affect our business. Our total borrowings were "
    "₹1,234.56 crore as of March 31, 2024."
)
GOOD = "Ten customers gave 62.48% of revenue in Fiscal 2024. Losing one may hurt the business."


def raw(simple: str = GOOD, **over: object) -> str:
    data: dict[str, object] = {
        "category": "customers_suppliers",
        "seriousness_1to5": 3,
        "hard_fact": False,
        "simple": simple,
        "numbers_copied": ["62.48%", "2024"],
    }
    data.update(over)
    return json.dumps(data)


# ------------------------------------------------------------------ prompt and schema
def test_ten_categories_and_the_prompt_lists_every_one() -> None:
    assert len(CATEGORIES) == 10
    system, user = messages("We depend on a few customers", "Body text.")
    assert system["role"] == "system"
    assert user["role"] == "user"
    for c in CATEGORIES:
        assert c in system["content"]
    assert user["content"].startswith("Title: We depend on a few customers")
    assert messages("  ", "Body only.")[1]["content"] == "Body only."


def test_schema_has_the_b03_fields() -> None:
    props = OUTPUT_SCHEMA["properties"]
    assert set(props) == {"category", "seriousness_1to5", "hard_fact", "simple", "numbers_copied"}
    assert set(props["category"]["enum"]) == set(CATEGORIES)


# ------------------------------------------------------------------ parsing
def test_parse_tolerates_think_blocks_and_code_fences() -> None:
    text = "<think>hmm</think>\n```json\n" + raw() + "\n```"
    out = parse_output(text)
    assert out.category == "customers_suppliers"
    assert out.seriousness_1to5 == 3


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("no json here", "invalid_json"),
        ("{not: json}", "invalid_json"),
        (raw(category="weather"), "bad_category"),
        (raw(seriousness_1to5=9), "bad_schema"),
        (raw(simple=""), "bad_schema"),
    ],
)
def test_parse_errors_carry_a_reason(text: str, reason: str) -> None:
    with pytest.raises(ParseError) as err:
        parse_output(text)
    assert err.value.reason == reason


# ------------------------------------------------------------------ checks
def test_numbers_must_come_from_the_original() -> None:
    assert unmatched_numbers(ORIGINAL, GOOD) == []
    assert unmatched_numbers(ORIGINAL, "Debt was ₹1,235 crore.") == []  # rounding allowed
    assert unmatched_numbers(ORIGINAL, "Ten customers gave 65% of revenue.") == ["65%"]
    assert unmatched_numbers(ORIGINAL, "Its 7 plants may close.") == ["7"]


def test_certainty_is_kept() -> None:
    assert certainty_changed(ORIGINAL, GOOD) is None
    assert certainty_changed(ORIGINAL, "Losing one will hurt the business.") == "hedge_dropped"
    fact = "We have incurred losses in Fiscal 2024."
    assert certainty_changed(fact, "The company lost money in Fiscal 2024.") is None
    assert certainty_changed(fact, "The company may have lost money.") == "hedge_added"
    assert certainty_changed(ORIGINAL, "Losing one may hurt. It will always matter.") == (
        "definite_added"
    )


def test_word_count() -> None:
    assert word_count("one two  three\nfour") == 4


# ------------------------------------------------------------------ filters
@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("oops", "invalid_json"),
        (raw(category="weather"), "bad_category"),
        (raw(hard_fact="perhaps"), "bad_schema"),
        (raw("Ten customers gave 65% of revenue and losing one may hurt."), "number_mismatch"),
        (raw("Losing a customer may hurt. You should avoid this IPO."), "forbidden_phrase"),
        (raw("Losing a customer may hurt. " + "word " * MAX_WORDS), "too_long"),
        (raw("Losing a customer will hurt the business."), "certainty_changed"),
    ],
)
def test_each_check_names_its_drop_reason(text: str, reason: str) -> None:
    out, got, _ = check_one(TeacherItem("r1", ORIGINAL, text))
    assert got == reason
    assert (out is None) == (reason in {"invalid_json", "bad_category", "bad_schema"})


def test_filter_keeps_good_drops_duplicates_and_reports_rates() -> None:
    items = [
        TeacherItem("r1", ORIGINAL, raw()),
        TeacherItem("r2", ORIGINAL, raw(GOOD.upper())),  # same rewrite, different case
        TeacherItem("r3", ORIGINAL, "nope"),
    ]
    report = filter_outputs(items)
    assert [k.risk_id for k in report.kept] == ["r1"]
    assert report.dropped == [("r2", "duplicate", ""), ("r3", "invalid_json", "")]
    summary = report.summary()
    assert summary["total"] == 3
    assert summary["kept"] == 1
    assert list(report.counts) == list(REASONS)
    assert summary["drop_rate"]["duplicate"] == pytest.approx(1 / 3)  # type: ignore[index]


def test_empty_input_reports_zero_rates() -> None:
    assert filter_outputs([]).summary()["drop_rate"] == {r: 0.0 for r in REASONS}
