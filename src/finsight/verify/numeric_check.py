"""Check one number of an answer against the retrieved passages (02 section 10.3, steps 3-4).

Every amount in the evidence is normalised and given the metric named before it. Then, for a
number in the answer:

- ✅ ``verified``: an evidence amount is equal within the printed precision, and nothing says
  it belongs to another metric.
- ❌ ``wrong_metric``: the value is in the evidence, but under a different metric, while the
  evidence gives another value for the metric the answer names (OFS amount called fresh issue).
- ❌ ``scale_mismatch``: an evidence amount differs by exactly a power of ten and either the
  printed digits are identical ("₹ 2,150 crore" vs "₹ 2,150 lakh", or a dropped "million") or
  the scale words differ and the gap is 10, 100 or 1,000 (ADR-027, ADR-044).
- ❌ ``wrong_value``: the evidence states this metric with a different value.
- ⚠️ ``placeholder``: the evidence has ``[●]`` for this metric and no real value.
- ⚠️ ``not_found``: the number is nowhere in the evidence.

Passages the sentence cites are searched first, so the evidence shown is the cited one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from finsight.core.schemas import (
    Amount,
    CheckResult,
    Claim,
    Count,
    Money,
    Passage,
    Placeholder,
    ReasonCode,
    Verdict,
)
from finsight.normalize import equal, parse_amounts
from finsight.verify.claims import mask_citations
from finsight.verify.metrics import find_metrics, metric_at

CHECK = "numeric"
MAX_POWER = 9  # identical digits: any unit slip up to a billion-fold
MAX_POWER_WORDS = 3  # different scale words, different digits: 10, 100, 1,000 only (ADR-027)
_DEVANAGARI_DIGITS = str.maketrans({chr(0x0966 + d): str(d) for d in range(10)})
_PRINTED = re.compile(r"\d[\d,]*(?:\.\d+)?")


@dataclass(frozen=True)
class EvidenceAmount:
    amount: Amount
    passage: Passage
    order: int  # position of the passage in the retrieved list, 0-based
    start: int
    end: int
    metric: str | None


def evidence_amounts(passages: list[Passage]) -> list[EvidenceAmount]:
    """Every amount in the passages with the metric that names it."""
    out = []
    for order, passage in enumerate(passages):
        spans = parse_amounts(passage.text)
        hits = find_metrics(passage.text)
        where = [(s.start, s.end) for s in spans]
        for s in spans:
            metric = metric_at(passage.text, s.start, s.end, hits, where)
            out.append(EvidenceAmount(s.amount, passage, order, s.start, s.end, metric))
    return out


def _as_money(amount: Amount) -> Money | None:
    """Money as it is; a share count as "money" so that printed precision and scale are known."""
    if isinstance(amount, Money):
        return amount if amount.value_inr is not None else None
    if isinstance(amount, Count):
        spans = parse_amounts(f"₹ {amount.raw}")
        if spans and isinstance(spans[0].amount, Money) and spans[0].amount.value_inr is not None:
            return spans[0].amount
    return None


def same_value(a: Amount, b: Amount) -> bool:
    """Equal within the printed precision; "8.18 crore shares" is 81,816,199 shares rounded."""
    if a.kind != b.kind:
        return False
    if isinstance(a, Count) and isinstance(b, Count):
        ma, mb = _as_money(a), _as_money(b)
        return a.value == b.value or (ma is not None and mb is not None and equal(ma, mb))
    return equal(a, b)


def _printed(money: Money) -> Decimal | None:
    m = _PRINTED.search(money.raw.translate(_DEVANAGARI_DIGITS))
    try:
        return Decimal(m.group().replace(",", "")) if m else None
    except InvalidOperation:
        return None


def power_of_ten_gap(a: Amount, b: Amount) -> int | None:
    """k when the two values differ by exactly 10**k (k >= 1), else None."""
    ma, mb = _as_money(a), _as_money(b)
    if a.kind != b.kind or ma is None or mb is None or ma.currency != mb.currency:
        return None
    if ma.value_inr is None or mb.value_inr is None:
        return None
    lo, hi = sorted((abs(ma.value_inr), abs(mb.value_inr)))
    if lo == 0:
        return None
    ratio = hi / lo
    for k in range(1, MAX_POWER + 1):
        if ratio == Decimal(10) ** k:
            return k
    return None


def is_scale_mismatch(a: Amount, b: Amount) -> bool:
    """A power-of-ten gap that comes from the unit, not from a different number (ADR-027)."""
    k = power_of_ten_gap(a, b)
    ma, mb = _as_money(a), _as_money(b)
    if k is None or ma is None or mb is None:
        return False
    if _printed(ma) is not None and _printed(ma) == _printed(mb):
        return True  # same digits, different or missing unit
    return ma.scale_word != mb.scale_word and k <= MAX_POWER_WORDS


def _where(e: EvidenceAmount) -> str:
    return f"passage [{e.order + 1}] (p. {e.passage.page_start})"


def _result(
    status: Verdict, code: ReasonCode, reason: str, answer: Amount, evidence: EvidenceAmount | None
) -> CheckResult:
    return CheckResult(
        check=CHECK,
        status=status,
        reason_code=code,
        reason=reason,
        answer_value=answer,
        evidence_value=evidence.amount if evidence else None,
        evidence_passage_id=evidence.passage.id if evidence else None,
        evidence_char_span=(evidence.start, evidence.end) if evidence else None,
    )


def check_number(
    amount: Amount, metric: str | None, evidence: list[EvidenceAmount], cited: list[int]
) -> CheckResult:
    """The verdict for one answer number. ``cited``: 1-based passage numbers of its sentence."""
    ordered = sorted(evidence, key=lambda e: (e.order + 1 not in cited, e.order, e.start))
    name = (metric or "").replace("_", " ")
    if isinstance(amount, Placeholder):
        blank = next((e for e in ordered if isinstance(e.amount, Placeholder)), None)
        if blank is None:
            reason = "No blank found in the passages."
            return _result("unverifiable", "not_found", reason, amount, None)
        reason = f"The document leaves this blank ([●]) in {_where(blank)}."
        return _result("unverifiable", "placeholder", reason, amount, blank)

    equals = [e for e in ordered if same_value(amount, e.amount)]
    named = [e for e in ordered if metric is not None and e.metric == metric]
    named_real = [e for e in named if not isinstance(e.amount, Placeholder)]
    other_values = [e for e in named_real if e.amount.kind == amount.kind and e not in equals]
    agreeing = [e for e in equals if metric is None or e.metric in (None, metric)]

    if agreeing:
        best = next((e for e in agreeing if e.metric == metric), agreeing[0])
        reason = f"Matches {_where(best)}: {best.amount.raw}."
        return _result("verified", "verified", reason, amount, best)
    if equals and other_values:
        e, real = equals[0], other_values[0]
        other = (e.metric or "").replace("_", " ")
        reason = (
            f"{e.amount.raw} is the {other} in {_where(e)}; the {name} there is {real.amount.raw}."
        )
        return _result("contradicted", "wrong_metric", reason, amount, e)
    if equals:  # the value is in the evidence; the passages give no other value for this metric
        e = equals[0]
        reason = f"Matches {_where(e)}: {e.amount.raw}."
        return _result("verified", "verified", reason, amount, e)

    near = [e for e in ordered if metric is None or e.metric in (None, metric)]
    slip = next((e for e in near if is_scale_mismatch(amount, e.amount)), None)
    if slip:
        times = 10 ** (power_of_ten_gap(amount, slip.amount) or 0)
        reason = (
            f"The answer says {amount.raw}; {_where(slip)} says {slip.amount.raw}: "
            f"a unit slip, {times:,}x apart."
        )
        return _result("contradicted", "scale_mismatch", reason, amount, slip)
    if other_values:
        e = other_values[0]
        reason = f"The {name} in {_where(e)} is {e.amount.raw}, not {amount.raw}."
        return _result("contradicted", "wrong_value", reason, amount, e)
    blank = next((e for e in named if isinstance(e.amount, Placeholder)), None)
    if blank:
        reason = f"The document leaves the {name} blank ([●]) in {_where(blank)}."
        return _result("unverifiable", "placeholder", reason, amount, blank)
    reason = f"{amount.raw} does not appear in the retrieved passages."
    return _result("unverifiable", "not_found", reason, amount, None)


class NumericCheck:
    """Implements ``core.interfaces.VerifierCheck``: one result per amount of the claim."""

    name = CHECK

    def check(self, claim: Claim, evidence: list[Passage]) -> list[CheckResult]:
        amounts = evidence_amounts(evidence)
        sentence = mask_citations(claim.sentence)
        spans = parse_amounts(sentence)
        hits = find_metrics(sentence)
        where = [(s.start, s.end) for s in spans]
        results = []
        for s in spans:
            metric = metric_at(sentence, s.start, s.end, hits, where)
            results.append(check_number(s.amount, metric, amounts, claim.cited))
        return results
