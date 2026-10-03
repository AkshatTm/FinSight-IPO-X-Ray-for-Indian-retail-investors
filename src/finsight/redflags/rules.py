"""The 13 checks (B01 §5) and their sentences (B05 §5.4, verbatim where B05 gives one).

Each check returns a ``Result``: status, sentence, the numbers it used (as shown) and the evidence
keys behind them. Thresholds come from ``configs/redflags.yaml``. A status without a B05 sentence
uses ``default_missing`` ("FinSight couldn't find this in the document."); the few sentences B05
does not give for a reachable status are builder drafts, listed in ``DRAFT_SENTENCES`` and in
docs/AKSHAT_TODO.md.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from finsight.core.schemas import Money, Status3
from finsight.normalize import group_digits, to_unit
from finsight.redflags.inputs import RedFlagInputs

# Sentences B05 §5.4 does not give, for statuses the rules can reach (copy to approve).
DRAFT_SENTENCES = {
    "RF01.ok_mixed": "Made a profit of ₹{pat} in the latest year.",
    "RF08.watch_unknown": "There are criminal cases involving the company, promoters or directors.",
    "RF10.ok": "The top customer brings in {t1}% of revenue{t10_part}.",
    "RF10.top10_only": "The top 10 customers bring in {t10}% of revenue.",
}


@dataclass
class Result:
    """What one check found."""

    status: Status3
    sentence: str
    numbers: dict[str, str] = field(default_factory=dict)
    evidence_keys: list[str] = field(default_factory=list)


# ------------------------------------------------------------------------- formatting
def money(m: Money) -> str:
    """A money value without the ₹ sign, in its own scale word, as the document wrote it."""
    scale = m.scale_word
    value = abs(to_unit(m, scale))
    if m.precision > 0:  # keep the printed decimals: "10.70" stays "10.70"
        value = value.quantize(Decimal(1).scaleb(-m.precision))
    text = group_digits(value, indian=scale in (None, "lakh", "crore", "lakh crore"))
    return f"{text} {scale}" if scale else text


def num(d: Decimal, places: int = 1) -> str:
    """A ratio or percentage for a sentence: rounded half up, without a trailing ".0"."""
    q = d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    text = f"{q:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _d(name: str, cfg: Mapping[str, Any]) -> Decimal:
    return Decimal(str(cfg[name]))


def _neg(m: Money | None) -> bool | None:
    return None if m is None or m.value_inr is None else m.value_inr < 0


def _ratio(a: Money | None, b: Money | None) -> Decimal | None:
    if a is None or b is None or a.value_inr is None or not b.value_inr:
        return None
    return a.value_inr / b.value_inr


Check = Callable[[RedFlagInputs, Mapping[str, Any], str], Result]


# ------------------------------------------------------------------------- the checks
def rf01(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    years = x.profit_after_tax
    latest = years[0] if years else None
    if latest is None:
        return Result("not_available", "FinSight couldn't find the profit figures.")
    pat = money(latest)
    used = {"pat": f"₹{pat}"}
    known = [m for m in years[:3] if m is not None]
    if len(known) == 3 and all(_neg(m) for m in known):
        return Result(
            "concern",
            f"Made a loss in each of the last 3 years (latest loss ₹{pat}).",
            used,
            ["profit_after_tax"],
        )
    if _neg(latest):
        return Result(
            "watch", f"Made a loss of ₹{pat} in the latest year.", used, ["profit_after_tax"]
        )
    if len(known) == 3 and not any(_neg(m) for m in known):
        return Result(
            "ok",
            f"Profitable in each of the last 3 years (latest profit ₹{pat}).",
            used,
            ["profit_after_tax"],
        )
    return Result(
        "ok", DRAFT_SENTENCES["RF01.ok_mixed"].format(pat=pat), used, ["profit_after_tax"]
    )


def rf02(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    years = x.operating_cash_flow
    latest = years[0] if years else None
    if latest is None:
        return Result("not_available", na)
    ocf = money(latest)
    k = sum(1 for m in years[:3] if _neg(m))
    used = {"ocf": f"₹{ocf}", "negative_years": str(k)}
    if k >= int(c["concern_negative_years"]):
        return Result(
            "concern",
            f"The business has used more cash than it brought in for {k} of the last 3 years.",
            used,
            ["operating_cash_flow"],
        )
    if _neg(latest):
        return Result(
            "watch",
            f"The business used more cash than it brought in last year (₹{ocf}).",
            used,
            ["operating_cash_flow"],
        )
    return Result(
        "ok", f"The business brought in cash last year (₹{ocf}).", used, ["operating_cash_flow"]
    )


def rf03(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    if x.is_financial_company:
        return Result(
            "not_applicable", "Not applicable: borrowing is a normal part of a lender's business."
        )
    de = _ratio(x.total_borrowings, x.net_worth)
    if de is None or (
        x.net_worth and x.net_worth.value_inr is not None and x.net_worth.value_inr < 0
    ):
        return Result("not_available", na)
    used = {"debt_to_equity": num(de, 2)}
    keys = ["total_borrowings", "net_worth"]
    if de > _d("concern_above", c):
        return Result(
            "concern",
            f"Debt is {num(de, 2)}× its net worth, which is high for a company like this.",
            used,
            keys,
        )
    if de > _d("watch_above", c):
        return Result(
            "watch",
            f"Debt is {num(de, 2)}× its net worth, which is high for a company like this.",
            used,
            keys,
        )
    return Result("ok", f"Debt is {num(de, 2)}× its net worth.", used, keys)


def _fresh_ofs(x: RedFlagInputs) -> tuple[Decimal, Decimal] | None:
    fresh = (
        x.fresh_amount.value_inr
        if x.fresh_amount and x.fresh_amount.value_inr is not None
        else None
    )
    ofs = x.ofs_amount.value_inr if x.ofs_amount and x.ofs_amount.value_inr is not None else None
    if fresh is None and ofs is None:
        return None
    return fresh or Decimal(0), ofs or Decimal(0)


def rf04(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    split = _fresh_ofs(x)
    if split is None or sum(split) <= 0:
        return Result("not_available", na)
    fresh, ofs = split
    ofs_pct = ofs / (fresh + ofs) * 100
    fresh_pct = 100 - ofs_pct
    used = {"fresh_pct": num(fresh_pct), "ofs_pct": num(ofs_pct)}
    keys = ["fresh_issue_amount", "ofs_amount"]
    if ofs_pct > _d("concern_above_pct", c):
        status: Status3 = "concern"
    elif ofs_pct > _d("watch_above_pct", c):
        status = "watch"
    else:
        return Result("ok", f"{num(fresh_pct)}% of the money goes to the company.", used, keys)
    return Result(
        status,
        f"{num(ofs_pct)}% of the money goes to existing shareholders who are selling, "
        "not to the company.",
        used,
        keys,
    )


def rf05(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    if x.offer_price is None:
        return Result("not_available", "Not available until the price is set.")
    gap = _ratio(x.offer_price, x.waca)
    if gap is None or gap <= 0:
        return Result("not_available", na)
    price, waca, xs = money(x.offer_price), money(x.waca), num(gap)  # type: ignore[arg-type]
    used = {"price": f"₹{price}", "waca": f"₹{waca}", "x": xs}
    keys = ["offer_price", "waca_selling_shareholders"]
    sentence = (
        f"Selling shareholders bought their shares at an average of ₹{waca}. "
        f"The IPO price is ₹{price}, about {xs}× more."
    )
    if gap >= _d("concern_at_least", c):
        return Result("concern", sentence, used, keys)
    if gap >= _d("watch_at_least", c):
        return Result("watch", sentence, used, keys)
    return Result(
        "ok", f"The IPO price is {xs}× what selling shareholders paid on average.", used, keys
    )


def rf06(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    if not x.promoter_identifiable:
        return Result("concern", "This company has no identifiable promoter.", {}, [])
    p = x.promoter_post_pct
    if p is None:
        return Result("not_available", na)
    used, keys = {"p": num(p)}, ["promoter_holding_post_pct"]
    if p < _d("concern_below_pct", c):
        return Result("concern", f"Promoters will own only {num(p)}% after the IPO.", used, keys)
    if p < _d("watch_below_pct", c):
        return Result("watch", f"Promoters will own only {num(p)}% after the IPO.", used, keys)
    return Result("ok", f"Promoters will still own {num(p)}% of the company.", used, keys)


def rf07(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    split = _fresh_ofs(x)
    if split is not None and split[0] == 0 and split[1] > 0:
        return Result(
            "not_applicable", "Not applicable: the company receives no money from this IPO."
        )
    g = x.general_purposes_pct
    if g is None:
        return Result("not_available", na)
    used, keys = {"g": num(g)}, ["general_purposes_pct_of_fresh"]
    vague = (
        f"{num(g)}% of the new money is for general purposes or acquisitions that aren't named yet."
    )
    if g >= _d("concern_at_least_pct", c):
        return Result("concern", vague, used, keys)
    if g > _d("watch_above_pct", c):
        return Result("watch", vague, used, keys)
    return Result(
        "ok", f"{num(g)}% of the new money is for general or unspecified purposes.", used, keys
    )


def rf08(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    pct = _ratio(x.litigation_amount, x.net_worth)
    if pct is not None and x.net_worth and x.net_worth.value_inr and x.net_worth.value_inr > 0:
        pct = abs(pct) * 100
        if pct > _d("concern_above_pct_of_net_worth", c):
            amt = money(x.litigation_amount)  # type: ignore[arg-type]
            used = {"amt": f"₹{amt}", "pct": num(pct)}
            return Result(
                "concern",
                f"Pending cases involve ₹{amt}, about {num(pct)}% of the company's net worth.",
                used,
                ["litigation_amount_total", "net_worth"],
            )
    else:
        pct = None
    n, any_case = x.criminal_cases, x.criminal_any
    if n is not None and n > 0:
        return Result(
            "watch",
            f"There are {n} criminal case(s) involving the company, promoters or directors.",
            {"n": str(n)},
            ["criminal_cases_any"],
        )
    if n is None and any_case:
        return Result("watch", DRAFT_SENTENCES["RF08.watch_unknown"], {}, ["criminal_cases_any"])
    if (n == 0 or any_case is False) and pct is not None:
        return Result(
            "ok",
            "No criminal cases and the disputed amounts are small.",
            {"pct": num(pct)},
            ["criminal_cases_any", "litigation_amount_total"],
        )
    return Result("not_available", na)


def rf09(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    revenue = x.revenue[0] if x.revenue else None
    share = _ratio(x.rpt_total, revenue)
    if share is None:
        return Result("not_available", na)
    pct = abs(share) * 100
    rpt = money(x.rpt_total)  # type: ignore[arg-type]
    used, keys = {"rpt": f"₹{rpt}", "pct": num(pct)}, ["rpt_total", "revenue"]
    sentence = f"Business with related parties was ₹{rpt}, about {num(pct)}% of revenue."
    if pct > _d("concern_above_pct", c):
        return Result("concern", sentence, used, keys)
    if pct > _d("watch_above_pct", c):
        return Result("watch", sentence, used, keys)
    return Result("ok", sentence, used, keys)


def rf10(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    t1, t10 = x.customer_top1_pct, x.customer_top10_pct
    if t1 is None and t10 is None:
        return Result("not_available", "The document doesn't give customer shares.")
    used = {k: num(v) for k, v in (("t1", t1), ("t10", t10)) if v is not None}
    keys = [k for k, v in (("customer_top1_pct", t1), ("customer_top10_pct", t10)) if v is not None]
    if t1 is None:
        # Only the top-10 share is given: B05 has no sentence for that case.
        status: Status3 = (
            "watch" if t10 is not None and t10 > _d("watch_top10_above_pct", c) else "ok"
        )
        sentence = DRAFT_SENTENCES["RF10.top10_only"].format(t10=num(t10))  # type: ignore[arg-type]
        return Result(status, sentence, used, keys)
    t10_part = f", and the top 10 bring in {num(t10)}%" if t10 is not None else ""
    sentence = f"The top customer brings in {num(t1)}% of revenue{t10_part}."
    if t1 > _d("concern_top1_above_pct", c):
        return Result("concern", sentence, used, keys)
    if t1 > _d("watch_top1_above_pct", c) or (
        t10 is not None and t10 > _d("watch_top10_above_pct", c)
    ):
        return Result("watch", sentence, used, keys)
    return Result(
        "ok", DRAFT_SENTENCES["RF10.ok"].format(t1=num(t1), t10_part=t10_part), used, keys
    )


def rf11(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    latest = x.profit_after_tax[0] if x.profit_after_tax else None
    if _neg(latest) or (x.issuer_pe is not None and x.issuer_pe <= 0):
        return Result(
            "not_applicable", "Not applicable: P/E can't be calculated for a loss-making company."
        )
    pe, peer = x.issuer_pe, x.peer_median_pe
    if pe is None or peer is None or peer <= 0:
        return Result("not_available", na)
    used = {"pe": num(pe), "peer_pe": num(peer)}
    keys = ["issuer_pe", "peer_pe_list"]
    sentence = (
        f"At the IPO price, the P/E is {num(pe)}. "
        f"The listed peers named in the document have a median P/E of {num(peer)}."
    )
    ratio = pe / peer
    if ratio > _d("concern_above_x", c):
        return Result("concern", sentence, used, keys)
    if ratio > _d("watch_above_x", c):
        return Result("watch", sentence, used, keys)
    return Result("ok", sentence, used, keys)


def rf12(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    keys = ["auditor_remarks"]
    if x.auditor is None:
        return Result("not_available", na)
    if x.auditor == "qualified":
        return Result(
            "concern", f"The auditor gave a qualified opinion: {x.auditor_short}.", {}, keys
        )
    if x.auditor in ("emphasis", "caro"):
        return Result("watch", f"The auditor drew attention to: {x.auditor_short}.", {}, keys)
    return Result("ok", "No remarks from the auditor in the summary.", {}, keys)


def rf13(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result:
    p = x.pledged_pct
    if p is None:
        return Result("not_available", na)
    used, keys = {"pct": num(p)}, ["pledged_promoter_pct"]
    if p > _d("concern_above_pct", c):
        return Result(
            "concern",
            f"{num(p)}% of promoter shares are pledged as security for loans.",
            used,
            keys,
        )
    if p > 0:
        return Result(
            "watch", f"{num(p)}% of promoter shares are pledged as security for loans.", used, keys
        )
    return Result("ok", "No promoter shares are pledged.", used, keys)


CHECKS: dict[str, Check] = {
    f"RF{i:02d}": fn
    for i, fn in enumerate(
        (rf01, rf02, rf03, rf04, rf05, rf06, rf07, rf08, rf09, rf10, rf11, rf12, rf13), start=1
    )
}
