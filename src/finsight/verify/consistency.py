"""Do the numbers in one IPO agree with each other? (02 section 10.3, consistency checks)

A fresh issue plus an offer for sale is the whole offer, so ``fresh + OFS = total`` must hold
when all three are printed. A blank ``[●]`` or a missing value is never a mismatch: it is
reported as unverifiable, with the reason the X-Ray shows next to the field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from finsight.core.schemas import CheckResult, Money, Placeholder, Value
from finsight.normalize import MULTIPLIER, format_money

CHECK_TOTAL = "total_equals_fresh_plus_ofs"


@dataclass
class ConsistencyReport:
    """Cross-field arithmetic checks and the derived numbers."""

    checks: list[CheckResult] = field(default_factory=list)
    derived: dict[str, str] = field(default_factory=dict)  # decimal strings, as in 06


def _step(money: Money) -> Decimal:
    """The smallest unit the document printed: decimals x scale word."""
    scale = MULTIPLIER[money.scale_word] if money.scale_word else Decimal(1)
    return Decimal(10) ** -money.precision * scale


def _shown(money: Money) -> str:
    return format_money(money, money.scale_word) if money.value_inr is not None else money.raw


def _unverifiable(code: str, reason: str) -> CheckResult:
    status = "unverifiable"
    if code == "placeholder":
        return CheckResult(
            check=CHECK_TOTAL, status=status, reason_code="placeholder", reason=reason
        )
    return CheckResult(check=CHECK_TOTAL, status=status, reason_code="not_found", reason=reason)


def check_consistency(
    *,
    fresh: Value | None,
    ofs_amount: Value | None,
    total: Value | None,
    pure_ofs: bool = False,
) -> ConsistencyReport:
    """``fresh + ofs_amount == total`` and the derived shares of the issue.

    ``pure_ofs``: the company gets no proceeds, so the fresh issue counts as zero.
    """
    report = ConsistencyReport()
    named = {"fresh issue": fresh, "offer for sale": ofs_amount, "total": total}
    if pure_ofs and fresh is None:
        named["fresh issue"] = Money(
            value_inr=Decimal(0), currency="INR", raw="nil (pure offer for sale)", precision=0
        )
    blanks = [n for n, v in named.items() if isinstance(v, Placeholder)]
    missing = [n for n, v in named.items() if not isinstance(v, Money | Placeholder)]
    if blanks:
        report.checks.append(
            _unverifiable("placeholder", f"The {', '.join(blanks)} is still [●] in the document.")
        )
        return report
    if missing:
        report.checks.append(
            _unverifiable("not_found", f"No value found for the {', '.join(missing)}.")
        )
        return report

    amounts = [p for p in named.values() if isinstance(p, Money) and p.value_inr is not None]
    if len(amounts) != 3 or any(p.value_inr is None for p in amounts):
        report.checks.append(_unverifiable("not_found", "A value could not be read as money."))
        return report
    f, o, t = amounts
    assert f.value_inr is not None
    assert o.value_inr is not None
    assert t.value_inr is not None
    computed = f.value_inr + o.value_inr
    step = max(_step(f), _step(o), _step(t))
    summed = Money(value_inr=computed, currency="INR", raw=f"{computed}", precision=0)
    sum_text = format_money(summed, t.scale_word) if t.scale_word else f"{computed}"
    if abs(computed - t.value_inr) <= step:
        report.checks.append(
            CheckResult(
                check=CHECK_TOTAL, status="verified", reason_code="verified",
                reason=f"Fresh issue + offer for sale = {sum_text}, matching the total.",
                answer_value=summed, evidence_value=t,
            )
        )  # fmt: skip
    else:
        report.checks.append(
            CheckResult(
                check=CHECK_TOTAL, status="contradicted", reason_code="wrong_value",
                reason=(
                    f"Fresh issue + offer for sale = {sum_text}, "
                    f"but the total says {_shown(t)}."
                ),
                answer_value=summed, evidence_value=t,
            )
        )  # fmt: skip
    if t.value_inr > 0:
        pct = Decimal(100) / t.value_inr
        report.derived["fresh_share_pct"] = str(
            (f.value_inr * pct).quantize(Decimal("0.01"), ROUND_HALF_UP)
        )
        report.derived["ofs_share_pct"] = str(
            (o.value_inr * pct).quantize(Decimal("0.01"), ROUND_HALF_UP)
        )
    return report
