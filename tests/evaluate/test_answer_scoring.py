"""The bake-off's "correct" column: verifier-based, strict on unit and metric (ADR-020)."""

import pytest

from finsight.evaluate.answer_scoring import score_answer

FRESH = ("Fresh issue size", "₹26,260 MILLION")
TOTAL = ("Total issue size", "₹ 29,808 MILLION")


@pytest.mark.parametrize(
    ("answer", "field", "expected"),
    [
        ("The fresh issue is ₹ 26,260 million [1].", FRESH, "yes"),
        ("The fresh issue is ₹ 2,626 crore [1].", FRESH, "yes"),  # same value, other unit: the unit
        # rule of the prompt, not the scorer's, rejects a conversion
        ("फ्रेश इश्यू का आकार ₹ 26,260 million है [1]।", FRESH, "yes"),
        # the rated sheet's two false "yes" rows:
        ("फ्रेश इश्यू ₹10,527 million है और 81,816,199 शेयर ₹26.260 करोड़ के बराबर हैं [4][5]।", FRESH, "no"),
        ("कुल इश्यू साइज़ ₹3,548 million है [1]।", TOTAL, "no"),
        ("The fresh issue is ₹ 262.60 million [1].", FRESH, "no"),  # 100x too small
        ("The total issue size is ₹ 26,260 million [1].", TOTAL, "no"),  # another field's value
        ("I could not find this in the document.", FRESH, "no"),
    ],
)
def test_amount_answers(answer: str, field: tuple[str, str], expected: str) -> None:
    assert score_answer(answer, *field).correct == expected


def test_wrong_unit_is_named_as_scale_mismatch() -> None:
    score = score_answer("The fresh issue is ₹ 26,260 crore [1].", *FRESH)
    assert (score.correct, score.why) == ("no", "scale_mismatch")


def test_right_value_plus_a_contradicting_figure_is_partial() -> None:
    score = score_answer("The fresh issue is ₹ 26,260 million, or ₹ 26,260 crore [1].", *FRESH)
    assert score.correct == "partial"


def test_names_are_matched_without_case_or_punctuation() -> None:
    assert score_answer("The registrar is KFin Technologies Limited [1].", "Registrar",
                        "KFin Technologies Limited").correct == "yes"  # fmt: skip
    assert score_answer("The registrar is Link Intime [1].", "Registrar",
                        "KFin Technologies Limited").correct == "no"  # fmt: skip


def test_per_share_values() -> None:
    assert (
        score_answer("Each share has a face value of ₹ 1 [1].", "Face value", "₹ 1").correct
        == "yes"
    )
    assert score_answer("The face value is ₹ 10 [1].", "Face value", "₹ 1").correct == "no"
