from decimal import Decimal

import pytest

from finsight.core.schemas import Money
from finsight.normalize import equal, format_money, group_digits, parse_amount, to_unit


def A(text: str):  # type: ignore[no-untyped-def]
    amount = parse_amount(text)
    assert amount is not None, text
    return amount


@pytest.mark.parametrize(
    ("a", "b", "same"),
    [
        ("₹ 1,250 crore", "₹ 12,499.8 million", True),  # the 02 section 10.4 example
        ("₹ 800 crore", "₹ 8,000 million", True),
        ("₹ 800 crore", "₹ 800 million", False),  # scale mismatch never rounds away
        ("₹ 800 crore", "₹ 80 crore", False),
        ("₹ 4.6 crore", "₹ 4.4 crore", False),
        ("₹ 5 crore", "₹ 4.6 crore", True),  # ₹ 5 crore is only precise to ₹ 1 crore
        ("₹ 50 lakh", "₹ 5 million", True),
        ("₹ 50 lakh", "₹ 0.5 crore", True),
        ("₹ 10", "₹ 1", False),  # face value ₹10 vs ₹1 (ADR-027 wrong_value)
        ("₹ 800 करोड़", "₹ 8,000 million", True),
        ("₹ 25 million", "US$ 25 million", False),
        ("10,000 shares", "10,000 equity shares", True),
        ("10,000 shares", "10,001 shares", False),
        ("12.5%", "12.54%", True),
        ("12.5%", "12.6%", False),
        ("12%", "12.4%", True),  # "12%" is precise to 1 pp
        ("150 bps", "1.5%", True),
        ("₹ 440 to ₹ 463", "₹440-₹463", True),
        ("₹ 440 to ₹ 463", "₹ 440 to ₹ 464", False),
        ("₹ 800 crore", "12.5%", False),
        ("[●]", "[●]", False),  # a blank is never equal, even to another blank
        ("₹ [●] crore", "₹ 800 crore", False),
    ],
)
def test_equal(a: str, b: str, same: bool) -> None:
    assert equal(A(a), A(b)) is same
    assert equal(A(b), A(a)) is same


def test_to_unit() -> None:
    m = A("₹ 800 crore")
    assert isinstance(m, Money)
    assert to_unit(m, "crore") == Decimal("800")
    assert to_unit(m, "million") == Decimal("8000")
    assert to_unit(m, "lakh") == Decimal("80000")
    assert str(to_unit(m, None)) == "8000000000"
    assert str(to_unit(A("₹ 12,499.8 million"), "crore")) == "1249.98"  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="no value"):
        to_unit(Money(value_inr=None, currency="INR", raw="x", precision=0), "crore")


@pytest.mark.parametrize(
    ("value", "indian", "text"),
    [
        ("12345678", True, "1,23,45,678"),
        ("12345678", False, "12,345,678"),
        ("100000.5", True, "1,00,000.5"),
        ("999", True, "999"),
        ("-1234.50", True, "-1,234.50"),
    ],
)
def test_group_digits(value: str, indian: bool, text: str) -> None:
    assert group_digits(Decimal(value), indian) == text


def test_format_money_gives_ui_equivalents() -> None:
    m = A("₹ 12,499.8 million")
    assert isinstance(m, Money)
    assert format_money(m, "crore") == "₹ 1,249.98 crore"
    assert format_money(m, "million") == "₹ 12,499.8 million"
    assert format_money(m, None) == "₹ 12,49,98,00,000"
