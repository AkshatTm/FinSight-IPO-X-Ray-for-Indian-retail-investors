"""Rules extractor tests. Sentences are real cover/offer wording from the three dev IPOs
(Ather Energy, Hexaware, Urban Company) as recorded in the gold quotes; nothing from test IPOs."""

from typing import Any

import pytest

from finsight.core.schemas import (
    Count,
    ListValue,
    Money,
    Page,
    ParsedDoc,
    Placeholder,
    Range,
    Section,
    TextValue,
)
from finsight.extract import RulesExtractor, get_field

URBAN_COVER = (
    "AN INITIAL PUBLIC OFFER OF UP TO [●] EQUITY SHARES OF FACE VALUE OF ₹1 EACH (THE "
    '"EQUITY SHARES") OF URBAN COMPANY LIMITED, COMPRISING A FRESH ISSUE OF [●] EQUITY SHARES '
    "AGGREGATING UP TO ₹ 4,720 MILLION BY OUR COMPANY AND AN OFFER FOR SALE OF [●] EQUITY "
    "SHARES AGGREGATING UP TO ₹ 14,280 MILLION BY THE SELLING SHAREHOLDERS. "
    "PROMOTERS OF OUR COMPANY: ABHIRAJ SINGH BHAL, RAGHAV CHANDRA AND VARUN KHAITAN "
    "DETAILS OF THE OFFER"
)
ATHER_COVER = (
    "INITIAL PUBLIC OFFER OF UP TO [●] EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH COMPRISING A "
    "FRESH ISSUE OF UP TO [●] EQUITY SHARES BY OUR COMPANY AGGREGATING UP TO ₹26,260 MILLION "
    "AND AN OFFER FOR SALE OF UP TO 11,051,746 EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH "
    "AGGREGATING TO ₹[●] MILLION BY THE SELLING SHAREHOLDERS"
)
HEXAWARE_COVER = (
    "INITIAL PUBLIC OFFER OF UP TO [●] EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH THROUGH AN OFFER "
    "FOR SALE OF UP TO [●] EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH AGGREGATING UP TO "
    "₹ 87,500 MILLION BY THE PROMOTER SELLING SHAREHOLDER. PROMOTER: CA MAGNUM HOLDINGS"
)
ATHER_PRO = (
    "INITIAL PUBLIC OFFER OF 100,000,000 EQUITY SHARES AT A PRICE OF ₹ 321^ PER EQUITY SHARE "
    "AGGREGATING UP TO ₹ 29,808 MILLION*^ COMPRISING A FRESH ISSUE"
)
URBAN_PRO = "THE OFFER PRICE IS ₹103^ PER EQUITY SHARE. AGGREGATING TO ₹ 19,000^ MILLION"
HEX_PRO = (
    "AT A PRICE OF ₹ 708* PER EQUITY SHARE OF FACE VALUE ₹ 1. AGGREGATING TO ₹ 87,500 MILLION^"
)


def make_doc(pages: list[str], doc_type: str = "rhp") -> ParsedDoc:
    return ParsedDoc(
        ipo_id="urban-company-2025", doc_type=doc_type, source_path="x.pdf", n_pages=len(pages),
        sha256="0", pages=[
            Page(number=i, width=595, height=842, words=[], text=t, is_scanned=False)
            for i, t in enumerate(pages, 1)
        ],
    )  # type: ignore[arg-type]  # fmt: skip


def run(
    field_id: str,
    *pages: str,
    doc_type: str = "rhp",
    sections: list[Section] | None = None,
) -> Any:
    doc = make_doc(list(pages), doc_type)
    return RulesExtractor().extract(doc, sections or [], [], get_field(field_id))


def best(field_id: str, *pages: str, **kw: Any) -> Any:
    cands = run(field_id, *pages, **kw)
    assert cands, f"no candidate for {field_id}"
    return cands[0]


def test_fresh_issue_amount_money_and_placeholder() -> None:
    c = best("fresh_issue_size", URBAN_COVER)
    assert isinstance(c.value, Money)
    assert c.value.value_inr == 4_720_000_000
    assert c.page == 1
    assert c.extractor == "rules"
    assert c.field_id == "fresh_issue_size"
    assert best("fresh_issue_size", ATHER_COVER).value.value_inr == 26_260_000_000


def test_fresh_issue_absent_in_a_pure_offer_for_sale() -> None:
    assert run("fresh_issue_size", HEXAWARE_COVER) == []


def test_ofs_shares_count_or_placeholder() -> None:
    c = best("ofs_shares", ATHER_COVER)
    assert isinstance(c.value, Count)
    assert c.value.value == 11_051_746
    assert isinstance(best("ofs_shares", URBAN_COVER).value, Placeholder)
    assert isinstance(best("ofs_shares", HEXAWARE_COVER).value, Placeholder)


def test_ofs_amount_money_or_placeholder() -> None:
    assert best("ofs_amount", URBAN_COVER).value.value_inr == 14_280_000_000
    assert best("ofs_amount", HEXAWARE_COVER).value.value_inr == 87_500_000_000
    assert isinstance(best("ofs_amount", ATHER_COVER).value, Placeholder)


def test_fresh_issue_does_not_pick_the_ofs_amount() -> None:
    c = best("fresh_issue_size", ATHER_COVER)
    assert c.value.value_inr == 26_260_000_000  # not the ₹[●] of the offer for sale


@pytest.mark.parametrize(
    ("text", "price"),
    [(ATHER_PRO, 321), (URBAN_PRO, 103), (HEX_PRO, 708)],
)
def test_offer_price_from_the_prospectus_cover(text: str, price: int) -> None:
    c = best("offer_price", text, doc_type="prospectus")
    assert isinstance(c.value, Money)
    assert c.value.value_inr == price


def test_offer_price_placeholder_in_an_rhp_sentence() -> None:
    c = best("offer_price", "AT A PRICE OF ₹ [●] PER EQUITY SHARE", doc_type="rhp")
    assert isinstance(c.value, Placeholder)


@pytest.mark.parametrize(
    "text",
    [
        "The price band ranging from the Floor Price of ₹ [●] per Equity Share",
        "Price band ranging from a Floor Price of ₹ [●] per Equity Share",
        "The price band of a minimum price of ₹ [●] per Equity Share",
    ],
)
def test_price_band_placeholder_in_all_dev_rhps(text: str) -> None:
    assert isinstance(best("price_band", text).value, Placeholder)


def test_price_band_range_when_printed() -> None:
    c = best("price_band", "The Price Band is ₹ 440 to ₹ 463 per Equity Share")
    assert isinstance(c.value, Range)
    assert (c.value.low.value_inr, c.value.high.value_inr) == (440, 463)
    also = best("price_band", "Price band of ₹ 103 - ₹ 108 per Equity Share")
    assert isinstance(also.value, Range)


@pytest.mark.parametrize(
    ("text", "total"),
    [(ATHER_PRO, 29_808_000_000), (URBAN_PRO, 19_000_000_000), (HEX_PRO, 87_500_000_000)],
)
def test_total_issue_size(text: str, total: int) -> None:
    c = best("total_issue_size", "INITIAL PUBLIC OFFER " + text, doc_type="prospectus")
    assert c.value.value_inr == total


def test_total_issue_size_is_the_first_amount_not_the_fresh_issue() -> None:
    text = (
        "AN INITIAL PUBLIC OFFER OF [●] EQUITY SHARES AGGREGATING UP TO ₹ 19,000 MILLION "
        "COMPRISING A FRESH ISSUE AGGREGATING UP TO ₹ 4,720 MILLION"
    )
    assert best("total_issue_size", text).value.value_inr == 19_000_000_000


def test_total_issue_size_placeholder_in_an_rhp() -> None:
    text = "INITIAL PUBLIC OFFER OF [●] EQUITY SHARES AGGREGATING UP TO ₹ [●] MILLION"
    assert isinstance(best("total_issue_size", text).value, Placeholder)


def test_face_value() -> None:
    assert best("face_value", ATHER_COVER).value.value_inr == 1
    assert best("face_value", "EQUITY SHARES OF FACE VALUE OF ₹1 EACH").value.value_inr == 1
    assert best("face_value", "equity shares of face value ₹ 10 each").value.value_inr == 10


def test_promoters_from_the_cover() -> None:
    c = best("promoters", URBAN_COVER)
    assert isinstance(c.value, ListValue)
    assert c.value.items == ["ABHIRAJ SINGH BHAL", "RAGHAV CHANDRA", "VARUN KHAITAN"]
    assert best("promoters", HEXAWARE_COVER).value.items == ["CA MAGNUM HOLDINGS"]
    ather = (
        "PROMOTERS OF OUR COMPANY: TARUN SANJAY MEHTA, SWAPNIL BABANLAL JAIN "
        "AND HERO MOTOCORP LIMITED"
    )
    assert best("promoters", ather).value.items == [
        "TARUN SANJAY MEHTA", "SWAPNIL BABANLAL JAIN", "HERO MOTOCORP LIMITED",
    ]  # fmt: skip


def test_registrar_known_and_generic() -> None:
    text = (
        "REGISTRAR TO THE OFFER NAME OF REGISTRAR CONTACT PERSON TELEPHONE AND E-MAIL "
        "MUFG Intime India Private Limited (Formerly Link Intime India Private Limited) "
        "Tel: +91 81 0811 4949"
    )
    c = best("registrar", text)
    assert isinstance(c.value, TextValue)
    assert c.value.text == "MUFG Intime India Private Limited"
    kfin = (
        "REGISTRAR TO THE OFFER NAME OF REGISTRAR Tel: (+91) 40 6716 2222 KFin Technologies Limited"
    )
    assert best("registrar", kfin).value.text == "KFin Technologies Limited"
    generic = "REGISTRAR TO THE OFFER Acme Share Services Private Limited Tel: 1"
    assert best("registrar", generic).value.text == "Acme Share Services Private Limited"


def test_brlms_skip_contact_details() -> None:
    text = (
        "BOOK RUNNING LEAD MANAGERS NAME AND LOGO CONTACT TELEPHONE AND E-MAIL PERSON(S) "
        "Tel: +91 22 4325 2183 Axis Capital Limited Sagar Jatakiya E-mail: a@axiscap.in "
        "HSBC Securities and Capital Markets (India) Private Limited Harsh Thakkar "
        "JM Financial Limited Prachee Dhuri REGISTRAR TO THE OFFER"
    )
    c = best("book_running_lead_managers", text)
    assert isinstance(c.value, ListValue)
    assert c.value.items == [
        "Axis Capital Limited",
        "HSBC Securities and Capital Markets (India) Private Limited",
        "JM Financial Limited",
    ]


def test_brlms_stop_at_the_registrar() -> None:
    text = (
        "BOOK RUNNING LEAD MANAGERS Axis Capital Limited REGISTRAR TO THE OFFER "
        "KFin Technologies Limited"
    )
    assert best("book_running_lead_managers", text).value.items == ["Axis Capital Limited"]


def test_hits_carry_the_pdf_page_and_earlier_pages_score_higher() -> None:
    cands = run("face_value", "cover with nothing", "EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH")
    assert cands[0].page == 2
    later = run("face_value", "x", "y", "EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH")
    assert later[0].score < cands[0].score


def test_section_pages_are_searched_beyond_the_cover() -> None:
    pages = ["filler"] * 29 + ["Fresh Issue of [●] Equity Shares aggregating up to ₹ 800 crore"]
    section = Section(
        id="the_offer", title="The Offer", start_page=30, end_page=30, method="toc", confidence=1.0
    )
    assert best("fresh_issue_size", *pages, sections=[section]).page == 30
    assert run("fresh_issue_size", *pages) == []  # the cover window is only the first pages


def test_no_match_gives_no_candidates() -> None:
    for fid in ("fresh_issue_size", "ofs_shares", "price_band", "promoters", "registrar"):
        assert run(fid, "The company designs electric scooters.") == []


def test_table_field_is_not_handled_by_the_rules_extractor() -> None:
    assert run("objects_of_offer", URBAN_COVER) == []


def test_brlm_table_split_over_a_page_break_gives_one_list() -> None:
    p1 = "BOOK RUNNING LEAD MANAGERS Kotak Mahindra Capital Company Limited Ganesh Rane"
    p2 = "IIFL Capital Services Limited (formerly known as IIFL Securities Limited) Mukesh"
    c = best("book_running_lead_managers", p1, p2)
    assert isinstance(c.value, ListValue)
    assert c.value.items == [
        "Kotak Mahindra Capital Company Limited",
        "IIFL Capital Services Limited",
    ]
    assert c.page == 1


def test_promoter_honorifics_do_not_cut_the_list() -> None:
    text = "PROMOTERS OF OUR COMPANY: MR. GYANENDRA KUMAR AND MRS. ASHA RANI. DETAILS OF THE OFFER"
    assert best("promoters", text).value.items == ["GYANENDRA KUMAR", "ASHA RANI"]


def test_pte_ltd_is_not_the_end_of_the_promoter_list() -> None:
    text = "OUR PROMOTERS: FOSUN PHARMA INDUSTRIAL PTE. LTD AND ACME HOLDINGS LIMITED. INITIAL"
    items = best("promoters", text).value.items
    assert items == ["FOSUN PHARMA INDUSTRIAL PTE. LTD", "ACME HOLDINGS LIMITED"]


def test_initials_do_not_end_the_promoter_list() -> None:  # audit miss, ADR-041
    text = (
        "PROMOTERS: M.G. GEORGE MUTHOOT, GEORGE THOMAS MUTHOOT, GEORGE JACOB MUTHOOT AND "
        "GEORGE ALEXANDER MUTHOOT table C M YK"
    )
    assert best("promoters", text).value.items == [
        "M.G. GEORGE MUTHOOT",
        "GEORGE THOMAS MUTHOOT",
        "GEORGE JACOB MUTHOOT",
        "GEORGE ALEXANDER MUTHOOT",
    ]
    text = "PROMOTERS OF OUR COMPANY: A. VELLAYAN AND ASHA RANI. DETAILS OF THE OFFER"
    assert best("promoters", text).value.items == ["A. VELLAYAN", "ASHA RANI"]
