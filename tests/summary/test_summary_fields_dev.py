"""C3.1b on real pages of the three **dev** IPOs in the fixture pack (C-ADR-02: tune on dev only).

Expected values are what each RHP prints (pages in the comments); sums and weighted averages
are worked out from the printed cells. Test-slice fixture IPOs are deliberately not pinned here.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from real import loader

from finsight.compare import peer_median_pe
from finsight.core.schemas import Count, FinancialSummary, Money
from finsight.redflags import evaluate, inputs_from_summary
from finsight.summary import extract_summary

DEV = ("ather-energy-2025", "hexaware-technologies-2025", "urban-company-2025")


@pytest.fixture(scope="module")
def summaries() -> dict[str, FinancialSummary]:
    return {
        ipo: extract_summary(
            loader.load_doc(ipo),
            loader.load_sections(ipo),
            subsections=loader.kept_pages(ipo),
            tables=loader.load_tables(ipo),
        )
        for ipo in DEV
    }


# ipo -> (criminal cases, aggregate amount in ₹, summary page)
LITIGATION = {
    "ather-energy-2025": (12, Decimal("102600580000"), 31),  # p31-32: 1,161.98 + 101,438.60 mn
    "hexaware-technologies-2025": (2, Decimal("7444000000"), 22),  # 7,244 + 200; USD/EUR left out
    "urban-company-2025": (4, Decimal("695320000"), 30),  # 123.18 + 536.65 + 22.50 + 12.99
}


@pytest.mark.parametrize("ipo", DEV)
def test_litigation(summaries: dict[str, FinancialSummary], ipo: str) -> None:
    n, amount, page = LITIGATION[ipo]
    lit = summaries[ipo].litigation
    criminal, total = lit["criminal_cases"], lit["amount_total"]
    assert isinstance(criminal.value, Count)
    assert (criminal.status, criminal.value.value) == ("found", n)
    assert isinstance(total.value, Money)
    assert (total.status, total.value.value_inr) == ("found", amount)
    assert criminal.evidence is not None
    assert total.evidence is not None
    assert (criminal.evidence.page, total.evidence.page) == (page, page)
    assert (total.evidence.sentence or "").startswith("[aggregate amount involved, sum of")


def test_foreign_currency_amounts_are_left_out_and_named(
    summaries: dict[str, FinancialSummary],
) -> None:
    ev = summaries["hexaware-technologies-2025"].litigation["amount_total"].evidence
    assert ev is not None
    assert "left out: Against the Subsidiaries: USD 2 million" in (ev.sentence or "")


def test_unquantified_amounts_are_left_out(summaries: dict[str, FinancialSummary]) -> None:
    ev = summaries["urban-company-2025"].litigation["amount_total"].evidence
    assert ev is not None
    assert "Not quantifiable" in (ev.sentence or "")


@pytest.mark.parametrize(("ipo", "page"), [("ather-energy-2025", 28), ("urban-company-2025", 27)])
def test_post_offer_holding_is_a_placeholder_in_an_rhp(
    summaries: dict[str, FinancialSummary], ipo: str, page: int
) -> None:
    post = summaries[ipo].promoter_holding_post
    assert post is not None
    assert (post.status, post.value) == ("placeholder", None)
    assert post.evidence is not None
    assert post.evidence.page == page


def test_offer_for_sale_only_ipo_has_no_gcp_and_no_post_table(
    summaries: dict[str, FinancialSummary],
) -> None:
    hexa = summaries["hexaware-technologies-2025"]
    assert hexa.general_purposes_pct is None
    assert hexa.promoter_holding_post is None


@pytest.mark.parametrize("ipo", ["ather-energy-2025", "urban-company-2025"])
def test_general_purposes_is_a_placeholder_in_an_rhp(
    summaries: dict[str, FinancialSummary], ipo: str
) -> None:
    gcp = summaries[ipo].general_purposes_pct
    assert gcp is not None
    assert gcp.status == "placeholder"
    assert gcp.evidence is not None
    assert gcp.evidence.page == 27


# ipo -> (promoters' weighted average ₹, promoter holders, selling shareholders' weighted
# average ₹, selling holders, page of the first row). None = no holder with a printed cost.
WACA = {
    "ather-energy-2025": (Decimal("113.18"), 3, Decimal("158.81"), 6, 44),  # IITM's "Nil" = 0
    "hexaware-technologies-2025": (Decimal("385.35"), 1, None, 0, 24),
    "urban-company-2025": (None, 0, Decimal("14.42"), 5, 36),  # founders' "Negligible": left out
}


@pytest.mark.parametrize("ipo", DEV)
def test_waca_promoters_and_selling_shareholders_are_separate(
    summaries: dict[str, FinancialSummary], ipo: str
) -> None:
    prom, n_prom, sell, n_sell, page = WACA[ipo]
    waca = summaries[ipo].waca
    by_key = {v.key: v for v in waca if v.key != "waca_holder"}
    holders = [v for v in waca if v.key == "waca_holder"]
    assert len(holders) == n_prom + n_sell
    for key, expected in (("waca_promoters", prom), ("waca_selling_shareholders", sell)):
        value = by_key.get(key)
        if expected is None:
            assert value is None
            continue
        assert value is not None
        assert isinstance(value.value, Money)
        assert value.value.value_inr == expected
        assert value.evidence is not None
        assert (value.evidence.sentence or "").startswith("[computed: share-weighted")
    sentences = [(h.evidence.sentence or "") for h in holders if h.evidence]
    assert sum(s.startswith("Promoter ") for s in sentences) == n_prom
    assert waca[0].evidence is not None
    assert waca[0].evidence.page == page
    assert not any(h.period.lower().startswith("last") for h in holders)


def test_peers(summaries: dict[str, FinancialSummary]) -> None:
    ather = summaries["ather-energy-2025"].peers  # p205
    assert [p.name for p in ather] == [
        "Our Company", "Hero MotoCorp Limited", "Bajaj Auto Limited",
        "Ola Electric Mobility Limited", "TVS Motors Limited", "Eicher Motors Limited",
    ]  # fmt: skip
    assert ather[0].is_issuer
    assert (ather[0].pe, ather[0].eps, ather[0].ronw) == (None, Decimal(-47), Decimal(-194))
    assert peer_median_pe(ather) == Decimal(33)
    hexa = summaries["hexaware-technologies-2025"].peers  # p257
    assert hexa[0].name == "Hexaware Technologies Limited"
    assert hexa[0].is_issuer
    assert (hexa[0].pe, hexa[0].eps, hexa[0].nav) == (None, Decimal("16.45"), Decimal("69.77"))
    assert [p.pe for p in hexa[1:]] == [Decimal(84), Decimal(64), Decimal(38), Decimal(34)]
    # Urban Company: "There are no listed companies in India or globally ..."
    assert summaries["urban-company-2025"].peers == []


def test_auditor_remarks(summaries: dict[str, FinancialSummary]) -> None:
    hexa = summaries["hexaware-technologies-2025"].auditor_remarks
    assert [v.evidence.page for v in hexa if v.evidence] == [22]
    assert str(hexa[0].value).startswith("There are no qualifications of the Statutory Auditors")
    ather = summaries["ather-energy-2025"].auditor_remarks
    assert [v.evidence.page for v in ather if v.evidence] == [31, 366]
    assert str(ather[1].value).startswith("Emphasis of Matter:")


@pytest.mark.parametrize("ipo", DEV)
def test_not_a_financial_company_and_promoter_identifiable(
    summaries: dict[str, FinancialSummary], ipo: str
) -> None:
    s = summaries[ipo]
    assert (s.is_financial_company, s.promoter_identifiable) == (False, True)


def test_customers_not_dated_are_not_found(summaries: dict[str, FinancialSummary]) -> None:
    # Hexaware's top-10 table puts a bare "2023" beside "twelve months ended September 30"
    # columns: the latest fiscal year cannot be told apart, so nothing is taken.
    hexa = summaries["hexaware-technologies-2025"]
    assert (hexa.customer_top1_pct, hexa.customer_top10_pct) == (None, None)


def test_red_flags_read_the_new_inputs(summaries: dict[str, FinancialSummary]) -> None:
    flags = {
        ipo: {f.id: f.status for f in evaluate(inputs_from_summary(s)).flags}
        for ipo, s in summaries.items()
    }
    # Ather: ₹102,600.58 mn in cases against a ₹5,459 mn net worth; an Emphasis of Matter.
    assert (flags[DEV[0]]["RF08"], flags[DEV[0]]["RF12"]) == ("concern", "watch")
    assert (flags[DEV[1]]["RF08"], flags[DEV[1]]["RF12"]) == ("concern", "ok")
    assert flags[DEV[2]]["RF08"] == "watch"  # 4 criminal cases; amounts small next to net worth
