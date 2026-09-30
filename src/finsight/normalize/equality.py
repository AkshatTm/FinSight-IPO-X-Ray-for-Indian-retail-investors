"""Are two amounts the same number? (02_ARCHITECTURE.md section 10.4)

Money is compared at the *coarser* stated precision: "₹ 1,250 crore" is only precise to
₹ 1 crore, so "₹ 12,499.8 million" (= ₹ 1,249.98 crore) rounds to the same ₹ 1,250 crore
and counts as equal. A 10x gap never rounds away, so "₹ 800 crore" vs "₹ 800 million" is
different. Counts must match exactly; percentages within 0.05 percentage points or the
coarser printed precision. A placeholder is never equal to anything, even another one.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from finsight.core.schemas import Amount, Count, Money, Percent, Range
from finsight.normalize.numerals import MULTIPLIER

PERCENT_TOLERANCE = Decimal("0.05")
_SYMBOL = {"INR": "₹", "USD": "US$", "OTHER": ""}


def _multiplier(scale: str | None) -> Decimal:
    return MULTIPLIER[scale] if scale else Decimal(1)


def _decimals(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def _round_to(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_HALF_UP)


def _money_equal(a: Money, b: Money) -> bool:
    if a.currency != b.currency or a.value_inr is None or b.value_inr is None:
        return False
    step_a = Decimal(10) ** -a.precision * _multiplier(a.scale_word)
    step_b = Decimal(10) ** -b.precision * _multiplier(b.scale_word)
    step = max(step_a, step_b)
    return _round_to(a.value_inr, step) == _round_to(b.value_inr, step)


def _percent_equal(a: Percent, b: Percent) -> bool:
    if abs(a.value - b.value) <= PERCENT_TOLERANCE:
        return True
    step = Decimal(10) ** -min(_decimals(a.value), _decimals(b.value))
    return _round_to(a.value, step) == _round_to(b.value, step)


def equal(a: Amount, b: Amount) -> bool:
    """Same kind, same currency and the same value within the stated precision."""
    if isinstance(a, Money) and isinstance(b, Money):
        return _money_equal(a, b)
    if isinstance(a, Count) and isinstance(b, Count):
        return a.value == b.value
    if isinstance(a, Percent) and isinstance(b, Percent):
        return _percent_equal(a, b)
    if isinstance(a, Range) and isinstance(b, Range):
        return _money_equal(a.low, b.low) and _money_equal(a.high, b.high)
    return False  # placeholders, or different kinds


def to_unit(amount: Money, unit: str | None) -> Decimal:
    """``amount`` expressed in ``unit`` ("crore", "million", ...; None = rupees), exactly."""
    if amount.value_inr is None:
        raise ValueError(f"{amount.raw!r} has no value")
    value = amount.value_inr / _multiplier(unit)
    if value == value.to_integral_value():
        return value.quantize(Decimal(1))
    return value.normalize()


def group_digits(value: Decimal, indian: bool = True) -> str:
    """Group digits as 12,34,567.8 (Indian) or 1,234,567.8 (Western); Western digits only."""
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):f}".partition(".")
    if indian and len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        pairs: list[str] = []
        while len(head) > 2:
            head, pairs = head[:-2], [head[-2:], *pairs]
        whole = ",".join([head, *pairs, tail])
    elif not indian:
        whole = f"{int(whole):,}"
    return sign + whole + (f".{frac}" if frac else "")


def format_money(amount: Money, unit: str | None) -> str:
    """UI equivalent such as "₹ 1,249.98 crore" or "₹ 12,499.8 million"."""
    value = to_unit(amount, unit)
    indian = unit in (None, "lakh", "crore", "lakh crore")
    text = f"{_SYMBOL[amount.currency]} {group_digits(value, indian)}".strip()
    return f"{text} {unit}" if unit else text
