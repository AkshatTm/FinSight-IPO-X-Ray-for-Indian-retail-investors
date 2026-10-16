"""C3.4: the four Compare numbers from an X-Ray and a summary, and per-metric reference n."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from finsight.compare import compare, compare_metrics
from finsight.core.schemas import (
    Candidate,
    FieldResult,
    FinancialSummary,
    Money,
    Peer,
    Range,
    SummaryValue,
    Value,
    XRay,
)


def _money(inr: str) -> Money:
    return Money(value_inr=Decimal(inr), currency="INR", raw=inr, precision=0)


def _field(field_id: str, value: Value | None) -> FieldResult:
    chosen = (
        None
        if value is None
        else Candidate(
            field_id=field_id,
            extractor="rules",
            doc_type="rhp",
            raw="x",
            value=value,
            page=1,
            score=1.0,
        )
    )
    return FieldResult(
        field_id=field_id, chosen=chosen, candidates=[], verdict="verified",
        reason_code="verified", reason="", checks=[],
    )  # fmt: skip


def _xray(fields: list[FieldResult], derived: dict[str, str] | None = None) -> XRay:
    return XRay(
        ipo_id="x", company="X", built_at=datetime(2026, 1, 1, tzinfo=UTC), fields=fields,
        derived=derived or {},
    )  # fmt: skip


def _summary(waca: str | None, pe: str | None) -> FinancialSummary:
    s = FinancialSummary(doc_id="x")
    if waca is not None:
        s.waca = [
            SummaryValue(key="waca_promoters", value=_money(waca), status="found", period="w")
        ]
    if pe is not None:
        s.peers = [Peer(name="X", is_issuer=True, pe=Decimal(pe))]
    return s


def test_metrics_use_the_printed_price_and_the_derived_ofs_share() -> None:
    xray = _xray(
        [
            _field("total_issue_size", _money("10000000000")),
            _field("offer_price", _money("500")),
        ],
        {"ofs_share_pct": "40.00"},
    )
    metrics, price = compare_metrics(xray, _summary("125", "31.5"))
    assert price == Decimal(500)
    assert metrics == {
        "issue_size_inr": Decimal("10000000000"),
        "ofs_share": Decimal("0.4"),
        "insider_price_gap": Decimal("4.00"),
        "pe": Decimal("31.5"),
    }


def test_the_cap_of_the_price_band_stands_in_for_a_blank_price() -> None:
    band = Range(low=_money("450"), high=_money("480"), raw="450-480")
    xray = _xray([_field("price_band", band)])
    metrics, price = compare_metrics(xray, _summary("120", None))
    assert price == Decimal(480)
    assert metrics["insider_price_gap"] == Decimal("4.00")
    assert metrics["pe"] is None
    assert metrics["issue_size_inr"] is None


def test_a_zero_average_cost_or_missing_numbers_give_no_gap() -> None:
    xray = _xray([_field("offer_price", _money("500"))])
    assert compare_metrics(xray, _summary("0", None))[0]["insider_price_gap"] is None
    assert compare_metrics(xray, _summary(None, None))[0]["insider_price_gap"] is None
    assert compare_metrics(_xray([]), _summary("100", None))[1] is None


def test_percentile_n_is_per_metric_when_the_config_has_it() -> None:
    cfg = {
        "provisional": False,
        "corpus_n": 120,
        "metric_n": {"pe": 40},
        "reference_quantiles": {
            "pe": [float(i) for i in range(0, 110, 10)],
            "ofs_share": [i / 10 for i in range(11)],
        },
    }
    out = compare([], {"pe": Decimal(55), "ofs_share": Decimal("0.5")}, cfg)
    n = {p.metric: p.corpus_n for p in out.percentiles}
    assert n == {"ofs_share": 120, "pe": 40}
