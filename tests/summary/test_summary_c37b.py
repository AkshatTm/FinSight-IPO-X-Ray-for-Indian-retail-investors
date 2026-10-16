"""C3.7b: issuer P/E statement, pure-offer-for-sale general purposes, promoter % sanity."""

from __future__ import annotations

from decimal import Decimal

from finsight.core.schemas import Page, ParsedDoc, Peer, Section
from finsight.summary.objects import general_purposes
from finsight.summary.peers import extract_peers, issuer_pe_statement, with_issuer_pe

DOC = "synthetic-2025"


def _doc(text: str, section: str) -> tuple[ParsedDoc, list[Section]]:
    page = Page(number=1, width=595, height=842, words=[], text=text, is_scanned=False)
    doc = ParsedDoc(
        ipo_id=DOC, doc_type="prospectus", source_path="x.pdf", n_pages=1, pages=[page],
        sha256="0",
    )  # fmt: skip
    sec = Section(id=section, title=section, start_page=1, end_page=1, method="toc", confidence=1)
    return doc, [sec]


PE_TEXT = (
    "2. Price/Earning (“P/E”) ratio in relation to the Offer Price: Particulars P/E at the Offer "
    "Price (no. of times) Based on basic EPS for financial year ended March 31, 2025 62.05 "
    "Based on diluted EPS for financial year ended March 31, 2025 62.42 "
    "3. Industry Peer Group P/E ratio There are no listed companies"
)


def test_issuer_pe_is_read_from_the_basic_eps_row() -> None:
    doc, secs = _doc(PE_TEXT, "basis_for_offer_price")
    peer = issuer_pe_statement(doc, secs, DOC)
    assert peer is not None
    assert peer.is_issuer
    assert peer.pe == Decimal("62.05")  # basic wins over diluted
    assert peer.evidence is not None
    assert peer.evidence.page == 1
    assert [p.pe for p in extract_peers(doc, secs, DOC)] == [Decimal("62.05")]


def test_issuer_pe_placeholder_and_a_missing_year_are_not_numbers() -> None:
    blank = PE_TEXT.replace("62.05", "[●]").replace("62.42", "[●]")
    doc, secs = _doc(blank, "basis_for_offer_price")
    peer = issuer_pe_statement(doc, secs, DOC)
    assert peer is not None
    assert peer.pe is None
    # the text layer lost the figure and the year: "December 31," must not read as P/E 31
    lost = (
        "P/E ratio at the Offer Price (number of times) Based on Basic EPS for the financial year "
        "ended December 31, Based on Diluted EPS for the financial year ended December 31, "
        "3. Industry Peer Group P/E ratio"
    )
    doc, secs = _doc(lost, "basis_for_offer_price")
    assert issuer_pe_statement(doc, secs, DOC) is None


def test_the_statement_fills_only_a_blank_issuer_pe() -> None:
    table = [Peer(name="Our Company", is_issuer=True), Peer(name="Peer", pe=Decimal(30))]
    statement = Peer(name="Issuer", is_issuer=True, pe=Decimal("62.05"))
    assert with_issuer_pe(table, statement)[0].pe == Decimal("62.05")
    printed = [Peer(name="Our Company", is_issuer=True, pe=Decimal(50))]
    assert with_issuer_pe(printed, statement)[0].pe == Decimal(50)


def test_pure_offer_for_sale_is_a_stated_zero_general_purposes() -> None:
    text = (
        "Objects of the Offer. Our Company will not receive any proceeds from the Offer and "
        "all proceeds go to the Selling Shareholder."
    )
    doc, secs = _doc(text, "objects_of_the_offer")
    value = general_purposes(doc, secs, DOC)
    assert value is not None
    assert value.status == "stated_zero"
    assert value.evidence is not None
    assert "will not receive any proceeds" in (value.evidence.sentence or "")
