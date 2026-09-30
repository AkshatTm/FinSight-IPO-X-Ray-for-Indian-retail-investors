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


if __name__ == "__main__":
    print(build(Path(sys.argv[1] if len(sys.argv) > 1 else "fixture.pdf")))
