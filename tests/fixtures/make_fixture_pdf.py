"""Build the synthetic 4-page RHP used by the parse tests.

Generated at test time (PDFs are never committed). Run directly to write a copy:
    uv run python tests/fixtures/make_fixture_pdf.py out.pdf

Layout (A4-ish 595 x 842 points):
  page 1  cover: bold 20 pt title "RED HERRING PROSPECTUS", the fresh-issue sentence
  page 2  body with a repeated header "ACME LIMITED" and printed footer "2"
  page 3  body with the same header and printed footer "3"
  page 4  image only, no text (a "scanned" page)
Pages 2-3 plus the cover carry the header, so it repeats on > 50 % of pages.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

WIDTH, HEIGHT = 595, 842
HEADER = "ACME LIMITED"
FRESH = "Fresh Issue of up to [●] Equity Shares aggregating up to ₹ 800.00 crore"


def build(path: Path) -> Path:
    doc = pymupdf.open()
    for number in (1, 2, 3):
        page = doc.new_page(width=WIDTH, height=HEIGHT)
        page.insert_text((72, 40), HEADER, fontsize=8, fontname="helv")
        if number == 1:
            page.insert_text((72, 120), "RED HERRING PROSPECTUS", fontsize=20, fontname="hebo")
            # htmlbox embeds a fallback font with ₹ and ●; base-14 Helvetica cannot encode them.
            page.insert_htmlbox(
                pymupdf.Rect(72, 150, 520, 200), f'<p style="font-size:10px">{FRESH}</p>'
            )
        else:
            page.insert_text((72, 120), f"Body text on page {number} about the Offer.", fontsize=10)
            page.insert_text((290, 810), str(number), fontsize=9, fontname="helv")
    scanned = doc.new_page(width=WIDTH, height=HEIGHT)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.set_rect(pix.irect, (200, 200, 200))
    scanned.insert_image(pymupdf.Rect(72, 72, 520, 770), pixmap=pix)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


TABLE_ROWS = [
    ("Particulars", "Estimated Amount"),
    ("Gross Proceeds of the Fresh Issue", "4,720"),
    ("Less: Offer expenses", "220"),
    ("Net Proceeds", "4,500"),
]


def build_table_pdf(path: Path) -> Path:
    """One 'Objects of the Offer' page: heading, fresh-issue text, unit line, ruled 4x2 table."""
    doc = pymupdf.open()
    page = doc.new_page(width=WIDTH, height=HEIGHT)
    page.insert_text((72, 80), "OBJECTS OF THE OFFER", fontsize=14, fontname="hebo")
    page.insert_text(
        (72, 110), "The Offer comprises a Fresh Issue and an Offer for Sale.", fontsize=10
    )
    page.insert_text((380, 160), "(Rs. in million)", fontsize=9)
    top, height, cols = 170.0, 22.0, (72.0, 380.0, 520.0)
    for r, (label, amount) in enumerate(TABLE_ROWS):
        y0 = top + r * height
        spans = ((cols[0], cols[1]), (cols[1], cols[2]))
        for (x0, x1), text in zip(spans, (label, amount), strict=True):
            page.draw_rect(pymupdf.Rect(x0, y0, x1, y0 + height), color=(0, 0, 0), width=0.7)
            page.insert_text((x0 + 4, y0 + 15), text, fontsize=9)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


# ------------------------------------------------------------------ offer documents (B1.1a)
OFFER_KINDS = ("rhp", "drhp", "prospectus", "non_offer", "scanned", "password", "news_mention")

_BODY = (
    "The Company is engaged in the manufacture of specialty chemicals. Our revenue from "
    "operations grew over the last three Fiscals and we expect to continue to invest in "
    "capacity. Investors should read the section titled Risk Factors before investing. "
)
_COVERS: dict[str, tuple[str, list[str]]] = {
    "rhp": (
        "RED HERRING PROSPECTUS",
        [
            "Dated September 29, 2025. Please read Section 32 of the Companies Act, 2013.",
            "100% Book Built Offer. Initial public offering of up to [●] Equity Shares.",
            "Book Running Lead Managers: Alpha Capital Limited. Registrar to the Offer.",
        ],
    ),
    "drhp": (
        "DRAFT RED HERRING PROSPECTUS",
        [
            "Dated June 2, 2025. This Draft Red Herring Prospectus will be updated upon",
            "filing with the RoC. 100% Book Built Offer of Equity Shares filed with SEBI.",
            "Book Running Lead Managers: Alpha Capital Limited. Registrar to the Offer.",
        ],
    ),
    "prospectus": (
        "PROSPECTUS",
        [
            "Dated October 6, 2025. Please read Section 26 and 32 of the Companies Act.",
            "Red Herring Prospectus dated September 29, 2025 was filed with the RoC.",
            "Offer of 1,20,00,000 Equity Shares at Rs 250 per Equity Share. SEBI ICDR.",
        ],
    ),
    "non_offer": (
        "ANNUAL REPORT 2024-25",
        [
            "Chairman's message to shareholders on a year of steady growth.",
            "Corporate overview, board of directors and sustainability highlights.",
        ],
    ),
    # A newsletter that only mentions a prospectus in body text: not an offer document.
    "news_mention": (
        "MARKET WEEKLY",
        [
            "This week Acme Limited filed its draft red herring prospectus with the regulator.",
            "Analysts discussed the sector outlook and recent quarterly results.",
        ],
    ),
}


def build_offer_pdf(path: Path, kind: str, *, pages: int = 5) -> Path:
    """A small synthetic document of one kind (RHP, DRHP, Prospectus, non-offer, scanned,
    password-protected or a news page that only mentions a prospectus).

    Every text page carries ~400 characters of body text, so only ``scanned`` looks like a scan.
    """
    if kind not in OFFER_KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    cover_kind = "rhp" if kind in ("scanned", "password") else kind
    title, lines = _COVERS[cover_kind]
    doc = pymupdf.open()
    for number in range(1, pages + 1):
        page = doc.new_page(width=WIDTH, height=HEIGHT)
        if kind == "scanned":
            pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
            pix.set_rect(pix.irect, (220, 220, 220))
            page.insert_image(pymupdf.Rect(36, 36, 559, 806), pixmap=pix)
            page.insert_text((290, 820), str(number), fontsize=8)
            continue
        page.insert_text((72, 40), HEADER, fontsize=8, fontname="helv")
        y = 120.0
        if number == 1:
            page.insert_text((72, y), title, fontsize=20, fontname="hebo")
            y += 40
            for line in lines:
                page.insert_text((72, y), line, fontsize=9, fontname="helv")
                y += 16
        page.insert_textbox(pymupdf.Rect(72, y + 10, 520, 760), _BODY * 2, fontsize=10)
        page.insert_text((290, 810), str(number), fontsize=9, fontname="helv")
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "password":
        doc.save(
            path,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner-fixture",
            user_pw="user-fixture",
        )
    else:
        doc.save(path)
    doc.close()
    return path


# A Risk Factors section for the upload pipeline (B2.1a): TOC on page 2, section on 3-4.
RISK_TITLES = [
    "We depend on a small number of customers for most of our revenue.",
    "Our promoters have pledged a part of their shareholding with lenders.",
    "Changes in interest rates in India could increase our finance costs.",
]
_RISK_BODY = [
    "In Fiscal 2025 our top ten customers contributed 61.2% of our revenue from operations.",
    "The loss of any of them could reduce our revenue and our cash flows significantly.",
]


def build_rhp_with_risks(path: Path) -> Path:
    """Five pages: RHP cover, contents, Risk Factors (pages 3-4, two groups, three risks with
    bold titles), Introduction. Every page carries a running header and a printed number."""
    title, cover_lines = _COVERS["rhp"]
    doc = pymupdf.open()
    pages: list[list[tuple[str, str, float]]] = [
        [(title, "hebo", 20), *[(ln, "helv", 9) for ln in cover_lines]],
        [("TABLE OF CONTENTS", "hebo", 14), ("RISK FACTORS ................ 3", "helv", 10),
         ("INTRODUCTION ................ 5", "helv", 10)],
        [("RISK FACTORS", "hebo", 14),
         ("An investment in equity shares involves a high degree of risk.", "helv", 10),
         ("", "", 0), ("Internal Risks", "hebo", 10), ("", "", 0),
         (RISK_TITLES[0], "hebo", 10), *[(ln, "helv", 10) for ln in _RISK_BODY], ("", "", 0),
         (RISK_TITLES[1], "hebo", 10), ("As of 30 June 2025, 12% of promoter shares", "helv", 10)],
        [("were pledged to secure loans taken by the Company.", "helv", 10), ("", "", 0),
         ("External Risks", "hebo", 10), ("", "", 0),
         (RISK_TITLES[2], "hebo", 10),
         ("Most of our borrowings carry floating rates.", "helv", 10)],
        [("INTRODUCTION", "hebo", 14)],
    ]  # fmt: skip
    for number, lines in enumerate(pages, start=1):
        page = doc.new_page(width=WIDTH, height=HEIGHT)
        page.insert_text((72, 40), HEADER, fontsize=8, fontname="helv")
        y = 120.0
        for text, font, size in lines:
            if text:
                page.insert_text((72, y), text, fontsize=size, fontname=font)
            y += 16 if size < 14 else 28
        if number in (1, 5):
            page.insert_textbox(pymupdf.Rect(72, y + 10, 520, 760), _BODY * 2, fontsize=10)
        page.insert_text((290, 810), str(number), fontsize=9, fontname="helv")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def build_blank_pdf(path: Path, pages: int) -> Path:
    """``pages`` empty pages, for the page-limit edges (cheap even at 1,501 pages)."""
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page(width=WIDTH, height=HEIGHT)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


if __name__ == "__main__":
    print(build(Path(sys.argv[1] if len(sys.argv) > 1 else "fixture.pdf")))
