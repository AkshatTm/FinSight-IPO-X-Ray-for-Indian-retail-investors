"""Where each summary reader looks: the Summary of the Offer Document, or its stand-ins (CC-05b).

Most RHPs have a "Summary of the Offer Document" (SOD), and the readers read their tables there.
Some don't (Jio, 2026: the "Introduction" holds The Issue and the ``summary_*`` sections), and
then a reader looks in the chapter the SOD would have summarised: Capital Structure for the
promoter holding, WACA and pledges, Outstanding Litigation for court cases, the Summary of
Related Party Transactions for RPT. Section locations come from ``parse.find_sections``, which
maps the TOC's *printed* page numbers to PDF pages from the page footers (median offset as
fallback), so a front-matter offset never shifts a section.

When no SOD was detected, the 40 pages before Risk Factors (where ICDR puts the summary) are
still scanned after the stand-in chapter, so a summary the finder missed is not lost.
"""

from __future__ import annotations

from typing import Literal

from finsight.core.schemas import Section

SOD_ID = "summary"
SUMMARY_WINDOW = 40  # pages scanned before Risk Factors when no Summary section was detected

Purpose = Literal["financials", "holdings", "waca", "litigation", "rpt", "auditor", "objects"]

# Stand-in sections per reader, tried in order, with a page cap each.
FALLBACK: dict[str, tuple[tuple[str, int], ...]] = {
    "financials": (),  # the Summary Financial Information is read on its own already
    "holdings": (("capital_structure", 40),),
    "waca": (("capital_structure", 40), ("basis_for_offer_price", 20)),
    "litigation": (("outstanding_litigation", 25),),
    "rpt": (("summary_of_related_party_transactions", 10),),
    "auditor": (),
    "objects": (("objects_of_the_offer", 30),),
}


def section_pages(sections: list[Section], section_id: str, limit: int = 40) -> list[int]:
    """PDF pages of one section, at most ``limit`` from its start; ``[]`` when not found."""
    for s in sections:
        if s.id == section_id:
            return list(range(s.start_page, min(s.end_page, s.start_page + limit - 1) + 1))
    return []


def has_sod(sections: list[Section]) -> bool:
    """Whether the document has a detected Summary of the Offer Document."""
    return any(s.id == SOD_ID for s in sections)


def window_pages(sections: list[Section]) -> list[int]:
    """The pages just before Risk Factors (or the first 40 when it was not found either)."""
    rf = next((s.start_page for s in sections if s.id == "risk_factors"), None)
    if rf is None:
        return list(range(1, SUMMARY_WINDOW + 1))
    return list(range(max(1, rf - SUMMARY_WINDOW), rf))


def reader_pages(sections: list[Section], purpose: Purpose | None = None) -> list[int]:
    """Pages a reader scans, best first: the SOD; else the stand-in chapter(s), then the window.

    Args:
        sections: The document's detected sections (PDF page numbers).
        purpose: Which reader asks; ``None`` gives the SOD or the window only (old behaviour).
    """
    if pages := section_pages(sections, SOD_ID):
        return pages
    out: list[int] = []
    for section_id, cap in FALLBACK.get(purpose or "", ()):
        out += [p for p in section_pages(sections, section_id, cap) if p not in out]
    return out + [p for p in window_pages(sections) if p not in out]


def source_of(sections: list[Section], purpose: Purpose) -> str:
    """``sod`` or ``fallback:<section ids>`` (or ``window``), for the evidence and ``SODResult``."""
    if has_sod(sections):
        return "sod"
    ids = [sid for sid, _ in FALLBACK.get(purpose, ()) if section_pages(sections, sid)]
    return f"fallback:{','.join(ids)}" if ids else "window"


def scan_start(sections: list[Section]) -> int:
    """First page the severe scan reads: the SOD, else Risk Factors, else page 1."""
    for sid in (SOD_ID, "risk_factors"):
        if pages := section_pages(sections, sid, 1):
            return pages[0]
    return 1
