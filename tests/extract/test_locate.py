from finsight.core.schemas import Word
from finsight.extract import locate_bbox


def words(*items: tuple[str, float, float]) -> list[Word]:
    """(text, x0, top) with 10 pt wide, 10 pt tall boxes."""
    return [
        Word(text=t, bbox=(x, y, x + 10.0, y + 10.0), font_size=10.0, bold=False)
        for t, x, y in items
    ]


PAGE = words(
    ("Fresh", 10, 100), ("Issue", 22, 100), ("of", 34, 100), ("up", 46, 100), ("to", 58, 100),
    ("₹", 70, 100), ("26,260", 82, 100), ("million", 94, 100), ("by", 106, 100), ("our", 118, 100),
    ("Company", 10, 114),
)  # fmt: skip


def test_finds_a_money_value_split_over_words() -> None:
    assert locate_bbox(PAGE, "₹ 26,260 million") == (70.0, 100.0, 104.0, 110.0)


def test_ignores_case_and_punctuation() -> None:
    assert locate_bbox(PAGE, "fresh issue") == (10.0, 100.0, 32.0, 110.0)
    assert locate_bbox(PAGE, "26260 MILLION") is not None  # the comma does not matter
    assert locate_bbox(PAGE, "27,260 million") is None  # a different number is not a match


def test_falls_back_to_the_number_alone() -> None:
    assert locate_bbox(PAGE, "Rs. 26,260 MILLION") is not None


def test_a_match_that_wraps_is_boxed_on_its_first_line() -> None:
    assert locate_bbox(PAGE, "by our Company") == (106.0, 100.0, 128.0, 110.0)


def test_no_match_returns_none() -> None:
    assert locate_bbox(PAGE, "Registrar") is None
    assert locate_bbox(PAGE, "") is None
    assert locate_bbox([], "anything") is None


def test_short_values_are_not_boxed_because_they_are_ambiguous() -> None:
    assert locate_bbox(words(("1", 10, 10), ("1", 30, 10)), "₹ 1") is None
