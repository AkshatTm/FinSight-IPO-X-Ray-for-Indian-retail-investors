import pytest

from finsight.core import registry
from finsight.core.schemas import Page, ParsedDoc, Word
from finsight.parse.sections import (
    KEY_SECTIONS,
    _heading_matches,
    canonical_id,
    find_sections,
    find_toc_pages,
    parse_toc_lines,
    printed_to_pdf,
)


def _page(n: int, text: str, printed: str | None = None, bold: tuple[str, ...] = ()) -> Page:
    words = [
        Word(text=w, bbox=(72, 100, 90, 110), font_size=14 if w in bold else 9, bold=w in bold)
        for w in text.split()
    ]
    return Page(
        number=n, printed_page=printed, width=595, height=842,
        words=words, text=text, is_scanned=False,
    )  # fmt: skip


TOC = "\n".join(
    [
        "TABLE OF CONTENTS",
        "SECTION I: GENERAL ........................................ 1",
        "DEFINITIONS AND ABBREVIATIONS ............................. 1",
        "SECTION III: INTRODUCTION ................................. 3",
        "THE OFFER ................................................. 3",
        "CAPITAL STRUCTURE ......................................... 4",
        "OBJECTS OF THE OFFER ...................................... 6",
        "MANAGEMENT’S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS",
        "............................................................ 7",
    ]
)


def _doc() -> ParsedDoc:
    """PDF pages 1-2 cover, 3 TOC, then printed page k is PDF page k + 3."""
    pages = [
        _page(1, "RED HERRING PROSPECTUS\nACME LIMITED"),
        _page(2, "NOTICE TO INVESTORS"),
        _page(3, TOC),
        _page(4, "SECTION I: GENERAL\nDEFINITIONS AND ABBREVIATIONS\nterms", "1"),
        _page(5, "more definitions", "2"),
        _page(6, "SECTION III: INTRODUCTION\nTHE OFFER\nThe table", "3", ("THE", "OFFER")),
        _page(7, "CAPITAL STRUCTURE\nshare capital", "4", ("CAPITAL", "STRUCTURE")),
        _page(8, "capital continued", "5"),
        _page(9, "OBJECTS OF THE OFFER\nThe Net Proceeds", "6"),
        _page(10, "MANAGEMENT’S DISCUSSION AND ANALYSIS\nresults", "7"),
        _page(11, "the end", "8"),
    ]
    return ParsedDoc(
        ipo_id="acme-2025", doc_type="rhp", source_path="x.pdf",
        n_pages=len(pages), pages=pages, sha256="0" * 64,
    )  # fmt: skip


def test_find_toc_pages() -> None:
    assert find_toc_pages(_doc()) == [3]


def test_parse_toc_lines_joins_wrapped_titles_and_skips_parts() -> None:
    entries = parse_toc_lines(TOC.splitlines())
    titles = [e.title for e in entries]
    assert titles == [
        "DEFINITIONS AND ABBREVIATIONS",
        "THE OFFER",
        "CAPITAL STRUCTURE",
        "OBJECTS OF THE OFFER",
        "MANAGEMENT’S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS",
    ]
    assert [e.printed_page for e in entries] == [1, 3, 4, 6, 7]


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("THE OFFER", "the_offer"),
        ("Objects of the Offer", "objects_of_the_offer"),
        ("OBJECTS OF THE ISSUE", "objects_of_the_offer"),
        ("CAPITAL  STRUCTURE", "capital_structure"),
        ("SUMMARY OF THIS RED HERRING PROSPECTUS", "summary"),
        ("SUMMARY OF THE OFFER DOCUMENT", "summary"),
        ("SUMMARY OF THIS PROSPECTUS", "summary"),
        ("OFFER DOCUMENT SUMMARY", "summary"),
        ("OUR PROMOTERS AND PROMOTER GROUP", "our_promoters"),
        ("BASIS FOR OFFER PRICE", "basis_for_offer_price"),
        ("GENERAL INFORMATION", "general_information"),
        ("TERMS OF THE OFFER", "terms_of_the_offer"),
        ("CERTAIN U.S. TAX CONSIDERATIONS", "certain_u_s_tax_considerations"),
    ],
)
def test_canonical_ids(title: str, expected: str) -> None:
    assert canonical_id(title) == expected


def test_part_header_that_is_itself_a_section_is_kept() -> None:
    lines = [
        "SECTION II: RISK FACTORS ........................ 33",
        "SECTION III: INTRODUCTION ....................... 75",
        "THE OFFER ....................................... 75",
    ]
    entries = parse_toc_lines(lines)
    assert [(e.title, e.printed_page) for e in entries] == [("RISK FACTORS", 33), ("THE OFFER", 75)]


def test_heading_with_part_prefix_confirms_the_section() -> None:
    doc = _doc()
    doc.pages[5].text = "SECTION III - THE OFFER\nThe table"
    sections = {s.id: s for s in find_sections(doc)}
    assert sections["the_offer"].start_page == 6
    assert sections["the_offer"].confidence >= 0.9


def test_printed_to_pdf_uses_footer_numbers_then_median_offset() -> None:
    doc = _doc()
    assert printed_to_pdf(doc, 3) == 6
    doc.pages[7].printed_page = None  # printed "5" unreadable: median offset (+3) still finds it
    assert printed_to_pdf(doc, 5) == 8
    assert printed_to_pdf(doc, 500) == doc.n_pages  # clamped to the document


def test_find_sections_key_sections_and_ranges() -> None:
    sections = {s.id: s for s in find_sections(_doc())}
    assert set(KEY_SECTIONS) <= set(sections)
    assert (sections["cover"].start_page, sections["cover"].end_page) == (1, 2)
    assert (sections["the_offer"].start_page, sections["the_offer"].end_page) == (6, 6)
    assert (sections["capital_structure"].start_page, sections["capital_structure"].end_page) == (
        7,
        8,
    )
    assert sections["objects_of_the_offer"].start_page == 9
    assert sections["management_s_discussion_and_analysis"].end_page == 11  # last runs to the end


def test_toc_confirmed_by_heading_and_bold_font_gives_full_confidence() -> None:
    sections = {s.id: s for s in find_sections(_doc())}
    assert sections["the_offer"].method == "toc"
    assert sections["the_offer"].confidence == pytest.approx(1.0)
    # heading found but not bold: still confirmed, slightly lower
    assert 0.8 <= sections["objects_of_the_offer"].confidence < 1.0


def test_wrong_toc_page_is_corrected_by_the_heading_regex() -> None:
    doc = _doc()
    # Break the footer map so the TOC points at the wrong PDF page for CAPITAL STRUCTURE.
    doc.pages[6].printed_page = None
    doc.pages[7].printed_page = "4"
    sections = {s.id: s for s in find_sections(doc)}
    assert sections["capital_structure"].start_page == 7
    assert sections["capital_structure"].method == "font"


def test_missing_toc_falls_back_to_heading_regex() -> None:
    doc = _doc()
    doc.pages[2].text = "nothing useful here"
    sections = {s.id: s for s in find_sections(doc)}
    assert sections["the_offer"].start_page == 6
    assert sections["the_offer"].method in {"regex", "font"}
    assert sections["the_offer"].confidence < 1.0


def test_rhp_adapter_is_registered() -> None:
    from finsight.parse.rhp_adapter import register

    register()  # other tests may have cleared the registry
    adapter = registry.get("doc_adapter", "rhp")
    assert adapter.doc_type == "rhp"
    assert {s.id for s in adapter.sections(_doc())} >= set(KEY_SECTIONS)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("RESTATED FINANCIAL INFORMATION", "restated_financial_information"),
        ("RESTATED CONSOLIDATED FINANCIAL INFORMATION", "restated_financial_information"),
        ("FINANCIAL INFORMATION", "restated_financial_information"),
        ("SUMMARY OF FINANCIAL INFORMATION", "summary_financial_information"),
        ("OTHER FINANCIAL INFORMATION", "other_financial_information"),
        ("FINANCIAL INDEBTEDNESS", "financial_indebtedness"),
        ("OUTSTANDING LITIGATION AND MATERIAL DEVELOPMENTS", "outstanding_litigation"),
        ("Outstanding Litigation", "outstanding_litigation"),
    ],
)
def test_financial_section_ids(title: str, expected: str) -> None:
    assert canonical_id(title) == expected


def test_subsection_pages_found_inside_restated_section() -> None:
    from finsight.core.schemas import Section
    from finsight.parse.sections import find_subsection_pages

    pages = [
        _page(1, "RESTATED FINANCIAL INFORMATION\nIndependent Auditor's Examination Report\ntext"),
        _page(2, "Restated Consolidated Statement of Balance Sheet\nassets"),
        _page(3, "Restated Consolidated Statement of Cash Flows\noperating"),
        _page(4, "notes\nThe auditors drew an emphasis of matter on going concern"),
        _page(5, "outside"),
    ]
    doc = ParsedDoc(ipo_id="x", doc_type="rhp", source_path="x.pdf", n_pages=5, pages=pages,
                    sha256="0" * 64)  # fmt: skip
    sec = Section(id="restated_financial_information", title="R", start_page=1, end_page=4,
                  method="toc", confidence=1.0)  # fmt: skip
    found = find_subsection_pages(doc, [sec])
    assert found == {"cash_flows": [3], "auditors_report": [1, 4]}
    assert find_subsection_pages(doc, []) == {}


# ---- C1.3 regressions: real RHPs whose Risk Factors section was missed (batch run) ------------
BAD = chr(0xFFFD)  # a glyph the PDF font could not map


def test_wrapped_leaders_do_not_glue_a_pageless_title_to_the_next_entry() -> None:
    """Text extraction broke the dot leaders over several lines and lost some page numbers."""
    lines = [
        "TABLE OF CONTENTS",
        "SUMMARY OF THE ISSUE DOCUMENT",
        "." * 40,
        "SECTION II: RISK FACTORS " + "." * 60 + " 34",
        "THE ISSUE",
        "." * 40,
        "SUMMARY OF RESTATED FINANCIAL STATEMENTS " + "." * 20 + " 81",
        "CAPITAL STRUCTURE " + "." * 30,
        "." * 20 + " 98",
    ]
    entries = parse_toc_lines(lines)
    assert [(e.title, e.printed_page) for e in entries] == [
        ("RISK FACTORS", 34),
        ("SUMMARY OF RESTATED FINANCIAL STATEMENTS", 81),
        ("CAPITAL STRUCTURE", 98),  # a dotted title completed by the leader line that follows
    ]
    assert canonical_id(entries[0].title) == "risk_factors"


def test_unmapped_glyph_leaders_and_dashes_read_as_dots_and_hyphens() -> None:
    lines = [
        "TABLE OF CONTENTS",
        f"SECTION II {BAD} RISK FACTORS" + BAD * 30 + " 35",
        "THE OFFER " + BAD * 20 + " 40",
    ]
    assert [(e.title, e.printed_page) for e in parse_toc_lines(lines)] == [
        ("RISK FACTORS", 35),
        ("THE OFFER", 40),
    ]
    page = _page(7, f"SECTION II {BAD} RISK FACTORS" + chr(10) + "If we lose a key customer")
    assert _heading_matches(page, "RISK FACTORS")


def test_singular_risk_factor_title_is_the_risk_factors_section() -> None:
    assert canonical_id("RISK FACTOR") == "risk_factors"
    assert canonical_id("Risk Factors") == "risk_factors"


def test_risk_factors_found_by_heading_when_the_toc_has_no_usable_entry() -> None:
    nl = chr(10)
    pages = [
        _page(1, "RED HERRING PROSPECTUS"),
        _page(2, "TABLE OF CONTENTS" + nl + "." * 40),
        _page(3, "SECTION I: GENERAL" + nl + "DEFINITIONS"),
        _page(4, f"SECTION II {BAD} RISK FACTORS" + nl + "Internal risks"),
        _page(5, "more risks"),
        _page(6, "THE OFFER" + nl + "the table"),
    ]
    doc = ParsedDoc(ipo_id="x-2025", doc_type="rhp", source_path="x.pdf", n_pages=6,
                    pages=pages, sha256="0" * 64)  # fmt: skip
    rf = next(s for s in find_sections(doc) if s.id == "risk_factors")
    assert (rf.start_page, rf.end_page) == (4, 5)
