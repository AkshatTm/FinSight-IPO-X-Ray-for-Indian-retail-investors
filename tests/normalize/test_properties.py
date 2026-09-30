"""Property tests: an amount written in any supported style parses back to the same value."""

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from finsight.core.schemas import Count, Money, Placeholder
from finsight.normalize import (
    MULTIPLIER,
    equal,
    format_money,
    group_digits,
    parse_amount,
    parse_amounts,
)

SCALE_SPELLINGS = {
    None: [""],
    "thousand": ["thousand", "thousands", "हजार"],
    "lakh": ["lakh", "lakhs", "lac", "Lacs", "लाख"],
    "crore": ["crore", "crores", "Cr.", "cr", "करोड़", "करोड"],
    "million": ["million", "mn", "Million"],
    "billion": ["billion", "bn", "अरब"],
}
PREFIXES = ["₹", "₹ ", "Rs.", "Rs. ", "INR ", "Rupees ", "रु. "]
SPACES = [" ", " ", " "]
DEVANAGARI = str.maketrans({str(d): chr(0x0966 + d) for d in range(10)})


@st.composite
def written_amount(draw: st.DrawFn) -> tuple[str, Decimal, str | None, int]:
    """(text, expected rupees, scale, precision) for a randomly written amount."""
    units = draw(st.integers(min_value=0, max_value=10**9))
    precision = draw(st.integers(min_value=0, max_value=2))
    number = Decimal(units).scaleb(-precision)
    scale = draw(st.sampled_from(list(SCALE_SPELLINGS)))
    word = draw(st.sampled_from(SCALE_SPELLINGS[scale]))
    digits = group_digits(number, indian=draw(st.booleans()))
    if draw(st.booleans()):
        digits = digits.translate(DEVANAGARI)
    space = draw(st.sampled_from(SPACES))
    text = draw(st.sampled_from(PREFIXES)) + digits + (space + word if word else "")
    expected = number * (MULTIPLIER[scale] if scale else Decimal(1))
    return text, expected, scale, precision


@given(written_amount())
def test_any_written_amount_parses_to_its_value(case: tuple[str, Decimal, str | None, int]) -> None:
    text, expected, scale, precision = case
    amount = parse_amount(text)
    assert isinstance(amount, Money), text
    assert amount.value_inr == expected
    assert (amount.scale_word, amount.precision, amount.currency) == (scale, precision, "INR")


@given(written_amount(), st.sampled_from([None, "lakh", "crore", "million", "billion"]))
def test_format_in_another_unit_and_parse_back_is_equal(
    case: tuple[str, Decimal, str | None, int], unit: str | None
) -> None:
    amount = parse_amount(case[0])
    assert isinstance(amount, Money)
    again = parse_amount(format_money(amount, unit))
    assert isinstance(again, Money)
    assert again.value_inr == amount.value_inr
    assert equal(again, amount)


@given(written_amount(), st.sampled_from(["The Offer of ", "कुल ", "(", "total: "]))
def test_amount_inside_a_sentence_keeps_its_span(
    case: tuple[str, Decimal, str | None, int], before: str
) -> None:
    text = before + case[0] + " only."
    found = parse_amounts(text)
    assert len(found) == 1
    assert text[found[0].start : found[0].end] == case[0].strip()


@given(st.integers(min_value=0, max_value=10**12), st.booleans())
def test_any_grouping_of_an_integer_is_read_back(value: int, indian: bool) -> None:
    amount = parse_amount(group_digits(Decimal(value), indian) + " equity shares")
    assert isinstance(amount, Count)
    assert amount.value == value


@given(st.sampled_from(["[●]", "[•]", "[ ● ]", "₹ [●] crore", "₹[●]"]), written_amount())
def test_placeholder_is_never_equal_to_a_value(
    blank: str, case: tuple[str, Decimal, str | None, int]
) -> None:
    placeholder = parse_amount(blank)
    value = parse_amount(case[0])
    assert isinstance(placeholder, Placeholder)
    assert value is not None
    assert not equal(placeholder, value)
    assert not equal(value, placeholder)
