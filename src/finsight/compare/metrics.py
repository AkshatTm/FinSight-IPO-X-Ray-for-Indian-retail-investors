"""The four numbers a document puts on the Compare tab, from its X-Ray and summary.

Used by the ``compare`` stage (one upload) and by ``scripts/compare_reference.py`` (every IPO of
the reference window), so the issuer and the reference set are measured the same way.

- ``issue_size_inr``: the chosen total issue size.
- ``ofs_share``: offer-for-sale share of the issue (0-1), from the X-Ray's consistency check, else
  the OFS amount over the total.
- ``insider_price_gap``: offer price over the promoters' share-weighted average cost (the cap of
  the price band when the final price is not printed yet). Not computed when either is missing
  or the average cost is zero.
- ``pe``: the issuer's P/E at the offer price as the document prints it.

A number the document does not print is ``None``, never an estimate.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from finsight.core.schemas import FinancialSummary, Money, Range, Value, XRay

Metrics = dict[str, Decimal | None]

# Bounds a real mainboard IPO stays inside; a value outside is a misread (a year read as a P/E, a
# share count read as a size) and is left out rather than shown or averaged.
BOUNDS: dict[str, tuple[Decimal, Decimal]] = {
    "issue_size_inr": (Decimal(10**8), Decimal(10**12)),
    "ofs_share": (Decimal(0), Decimal(1)),
    "insider_price_gap": (Decimal("0.1"), Decimal(1000)),
    "pe": (Decimal(0), Decimal(500)),
}


def plausible(metric: str, value: object) -> bool:
    """Whether ``value`` is a number inside the metric's bounds (zero P/E excluded)."""
    if value is None:
        return False
    d = Decimal(str(value))
    lo, hi = BOUNDS[metric]
    return lo <= d <= hi and not (metric == "pe" and d == 0)


def _money(value: Value | None) -> Decimal | None:
    if isinstance(value, Money) and value.value_inr is not None and value.value_inr > 0:
        return value.value_inr
    return None


def _chosen(xray: XRay, field_id: str) -> Value | None:
    for f in xray.fields:
        if f.field_id == field_id and f.chosen is not None:
            return f.chosen.value
    return None


def offer_price(xray: XRay) -> Decimal | None:
    """The printed offer price, else the cap of the price band; ``None`` for ``[●]``."""
    if (price := _money(_chosen(xray, "offer_price"))) is not None:
        return price
    band = _chosen(xray, "price_band")
    return _money(band.high) if isinstance(band, Range) else None


def compare_metrics(xray: XRay, summary: FinancialSummary) -> tuple[Metrics, Decimal | None]:
    """``(metrics, offer_price)`` for ``finsight.compare.compare``."""
    total = _money(_chosen(xray, "total_issue_size"))
    share: Decimal | None = None
    raw = xray.derived.get("ofs_share_pct")
    if raw is not None:
        try:
            share = Decimal(raw) / 100
        except InvalidOperation:
            share = None
    if share is None and total is not None:
        ofs_value = _chosen(xray, "ofs_amount")
        ofs = _money(ofs_value)
        if ofs is not None:
            share = min(ofs / total, Decimal(1))
    price = offer_price(xray)
    waca = next((v for v in summary.waca if v.key == "waca_promoters"), None)
    waca_inr = _money(waca.value) if waca is not None else None
    gap = (price / waca_inr).quantize(Decimal("0.01")) if price and waca_inr else None
    issuer = next((p for p in summary.peers if p.is_issuer), None)
    metrics: Metrics = {
        "issue_size_inr": total,
        "ofs_share": share,
        "insider_price_gap": gap,
        "pe": issuer.pe if issuer is not None else None,
    }
    return {k: (v if plausible(k, v) else None) for k, v in metrics.items()}, price
