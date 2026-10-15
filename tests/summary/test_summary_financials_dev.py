"""C3.1a on real pages of the three **dev** IPOs in the fixture pack (C-ADR-02: tune on dev only).

Expected values are the figures printed in each RHP's restated financial summary and cash-flow
statement (pages in the comments). Test-slice fixture IPOs are deliberately not pinned here.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from real import loader

from finsight.core.config import project_root
from finsight.core.schemas import FinancialSummary, Money, ParsedDoc, Section
from finsight.redflags import evaluate, inputs_from_summary
from finsight.splits import load_splits
from finsight.summary import extract_summary

DEV = ("ather-energy-2025", "hexaware-technologies-2025", "urban-company-2025")

# ipo -> (unit, revenue, PAT, OCF (latest first), borrowings, net worth, summary page)
EXPECTED = {
    "ather-energy-2025": (
        "₹ in million",
        ["17,538", "17,809", "4,089"],
        ["(10,597)", "(8,645)", "(3,441)"],
        ["(2,676)", "(8,713)", "(2,284)"],  # p117, summary cash flows
        "3,149",
        "5,459",
        30,
    ),
    "hexaware-technologies-2025": (  # calendar fiscal year (December)
        "₹ in million",
        ["103,803", "91,996", "71,777"],
        ["9,976", "8,842", "7,488"],
        ["15,156", "8,206", "9,798"],  # p84
        "-",  # "Borrowings (secured)": a dash for 2023, a stated zero
        "42,309",
        21,
    ),
    "urban-company-2025": (
        "₹ in million",
        ["11,444.65", "8,280.18", "6,365.97"],
        ["2,397.65", "(927.72)", "(3,124.84)"],
        ["545.58", "(855.75)", "(2,377.98)"],  # p327, restated cash-flow statement
        "-",
        "17,958.21",
        29,
    ),
}


@pytest.fixture(scope="module")
def summaries() -> dict[str, FinancialSummary]:
    return {
        ipo: extract_summary(
            loader.load_doc(ipo), loader.load_sections(ipo), subsections=loader.kept_pages(ipo)
        )
        for ipo in DEV
    }


def _raw(values: list) -> list[str | None]:  # type: ignore[type-arg]
    return [v.value.raw if isinstance(v.value, Money) else None for v in values]


def test_fixture_ipos_used_here_are_in_the_dev_slice() -> None:
    slices = {
        e.ipo_id: e.slice for e in load_splits(project_root() / "configs" / "splits.yaml").ipos
    }
    assert {slices[ipo] for ipo in DEV} == {"dev"}


@pytest.mark.parametrize("ipo", DEV)
def test_values(summaries: dict[str, FinancialSummary], ipo: str) -> None:
    s = summaries[ipo]
    unit, revenue, pat, ocf, borrowings, net_worth, _ = EXPECTED[ipo]
    assert s.currency_unit == unit
    assert _raw(s.revenue) == revenue
    assert _raw(s.profit_after_tax) == pat
    assert _raw(s.operating_cash_flow) == ocf
    assert _raw([s.total_borrowings]) == [borrowings]
    assert _raw([s.net_worth]) == [net_worth]
    assert [v.period for v in s.revenue] == ["latest", "latest-1", "latest-2"]


@pytest.mark.parametrize("ipo", DEV)
def test_every_value_is_found_with_page_and_box(
    summaries: dict[str, FinancialSummary], ipo: str
) -> None:
    s = summaries[ipo]
    page = EXPECTED[ipo][-1]
    values = [*s.revenue, *s.profit_after_tax, *s.operating_cash_flow]
    values += [s.total_borrowings, s.net_worth]
    for v in values:
        assert v is not None
        # Hexaware and Urban print "-" for borrowings in an otherwise numeric table.
        assert v.status == (
            "stated_zero" if v.key == "total_borrowings" and ipo != DEV[0] else "found"
        )
        assert v.evidence is not None
        assert v.evidence.bbox is not None
        assert v.evidence.sentence
        assert v.evidence.doc_id == ipo
    pages = {
        v.evidence.page for v in [*s.revenue, *s.profit_after_tax, s.net_worth] if v and v.evidence
    }
    assert pages == {page}


def test_money_is_scaled_and_signed(summaries: dict[str, FinancialSummary]) -> None:
    loss = summaries["ather-energy-2025"].profit_after_tax[0].value
    assert isinstance(loss, Money)
    assert loss.value_inr == Decimal("-10597000000")
    nil = summaries["urban-company-2025"].total_borrowings
    assert nil is not None
    assert isinstance(nil.value, Money)
    assert nil.value.value_inr == 0


def test_balance_sheet_primary_and_stub(summaries: dict[str, FinancialSummary]) -> None:
    ather = summaries["ather-energy-2025"]
    assert ather.net_worth is not None
    assert ather.net_worth.period == "latest"
    assert (ather.net_worth.evidence.sentence or "").startswith(
        "[primary: latest full fiscal year]"
    )
    stub, debt = ather.net_worth_stub, ather.total_borrowings_stub
    assert stub is not None
    assert debt is not None
    assert _raw([stub, debt]) == ["1,080", "11,216"]
    assert "December 31, 2024" in (stub.period or "")
    assert stub.evidence is not None
    assert (stub.evidence.sentence or "").startswith("[secondary: stub period]")
    # Hexaware's stub columns (Sept 2024) show 48,760 net worth.
    hexa = summaries["hexaware-technologies-2025"].net_worth_stub
    assert hexa is not None
    assert _raw([hexa]) == ["48,760"]


def test_stub_period_is_not_latest(summaries: dict[str, FinancialSummary]) -> None:
    # Ather's first columns are nine months to Dec 2024 (15,789): never the latest year.
    ev = summaries["ather-energy-2025"].revenue[0].evidence
    assert ev is not None
    assert "March 31, 2024" in (ev.sentence or "")


def test_feeds_the_red_flag_checks(summaries: dict[str, FinancialSummary]) -> None:
    flags = {f.id: f for f in evaluate(inputs_from_summary(summaries["ather-energy-2025"])).flags}
    assert flags["RF01"].status == "concern"  # a loss in each of the last 3 years
    assert flags["RF02"].status == "concern"  # cash used in all 3 years
    assert flags["RF03"].status == "ok"  # 3,149 / 5,459 = 0.58
    assert [e.page for e in flags["RF01"].evidence][:1] == [30]


def test_missing_sections_give_not_found() -> None:
    full = loader.load_doc("ather-energy-2025")
    # Without a Summary section the first 40 pages are scanned (no Risk Factors here either).
    doc = full.model_copy(update={"pages": [p for p in full.pages if p.number > 40]})
    only_cover: list[Section] = [s for s in loader.load_sections("ather-energy-2025")
                                 if s.id == "cover"]  # fmt: skip
    s = extract_summary(doc, only_cover, subsections={})
    assert s.currency_unit == ""
    assert {v.status for v in s.revenue} == {"not_found"}
    assert s.net_worth is not None
    assert s.net_worth.status == "not_found"


def test_placeholder_cells_are_placeholders() -> None:
    doc = loader.load_doc("ather-energy-2025")
    page = next(p for p in doc.pages if p.number == 30)
    words = [w.model_copy(update={"text": "[●]"}) if w.text == "17,538" else w for w in page.words]
    pages = [p if p.number != 30 else page.model_copy(update={"words": words}) for p in doc.pages]
    edited = ParsedDoc.model_validate(doc.model_dump() | {"pages": pages})
    s = extract_summary(edited, loader.load_sections("ather-energy-2025"), subsections={})
    assert s.revenue[0].status == "placeholder"
    assert s.revenue[0].value is None
    assert s.revenue[1].status == "found"
