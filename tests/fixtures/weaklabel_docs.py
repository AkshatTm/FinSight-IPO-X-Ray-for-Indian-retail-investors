"""Synthetic offer documents for the weaklabel tests (made up, not from real filings)."""

from __future__ import annotations

from finsight.core.schemas import Page, ParsedDoc, Section

COVER = (
    "INITIAL PUBLIC OFFER OF UP TO 10,000,000 EQUITY SHARES OF FACE VALUE OF ₹ 10 EACH OF ACME "
    "LIMITED AGGREGATING UP TO ₹ 5,000.00 MILLION COMPRISING A FRESH ISSUE OF 6,000,000 EQUITY "
    "SHARES AGGREGATING UP TO ₹ 3,000.00 MILLION AND AN OFFER FOR SALE OF 4,000,000 EQUITY SHARES "
    "AGGREGATING UP TO ₹ 2,000.00 MILLION. PROMOTERS OF OUR COMPANY: RAVI KUMAR AND ANITA DESAI. "
    "BOOK RUNNING LEAD MANAGERS Axis Capital Limited JM Financial Limited "
    "REGISTRAR TO THE OFFER KFin Technologies Limited Tel: 1"
)
OFFER = (
    "THE OFFER. The Offer comprises a fresh issue by our Company aggregating up to Rs. 300 crore "
    "and an offer for sale by the Selling Shareholders of 4,000,000 Equity Shares. "
    "Equity Shares outstanding prior to the Offer: 40,000,000 Equity Shares."
)
CAPITAL = (
    "CAPITAL STRUCTURE. Authorised share capital 60,000,000 Equity Shares of face value of ₹ 10 "
    "each. The registrar is KFin Technologies Ltd. and it maintains the register."
)
FILLER = "Our Company manufactures cement in Gujarat and sells it across western India."


def make_doc(pages: list[str], ipo_id: str = "acme-2019", kind: str = "prospectus") -> ParsedDoc:
    return ParsedDoc(
        ipo_id=ipo_id, doc_type=kind, source_path="x", n_pages=len(pages), sha256="",
        pages=[
            Page(number=i, width=0, height=0, words=[], text=t, is_scanned=False)
            for i, t in enumerate(pages, 1)
        ],
    )  # type: ignore[arg-type]  # fmt: skip


def sections_for(n_pages: int) -> list[Section]:
    return [
        Section(id="the_offer", title="The Offer", start_page=n_pages - 2, end_page=n_pages - 2,
                method="toc", confidence=1.0),
        Section(id="capital_structure", title="Capital Structure", start_page=n_pages - 1,
                end_page=n_pages, method="toc", confidence=1.0),
    ]  # fmt: skip


def acme() -> tuple[ParsedDoc, list[Section]]:
    pages = [COVER] + [FILLER] * 17 + [OFFER, CAPITAL, FILLER]  # 21 pages
    return make_doc(pages), sections_for(len(pages))
