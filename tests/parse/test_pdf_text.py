from pathlib import Path

import pytest
from PIL import Image

from finsight.core.schemas import ParsedDoc
from finsight.parse import parse_pdf, render_pages
from finsight.parse.clean import (
    boilerplate_keys,
    is_scanned_page,
    line_key,
    read_printed_page,
)


@pytest.fixture(scope="module")
def doc(fixture_pdf: Path) -> ParsedDoc:
    return parse_pdf(fixture_pdf, ipo_id="acme-2025", doc_type="rhp")


def test_document_metadata(doc: ParsedDoc, fixture_pdf: Path) -> None:
    assert doc.n_pages == 4
    assert [p.number for p in doc.pages] == [1, 2, 3, 4]
    assert doc.doc_type == "rhp"
    assert len(doc.sha256) == 64
    assert doc.source_path == fixture_pdf.as_posix()


def test_words_have_boxes_inside_the_page(doc: ParsedDoc) -> None:
    cover = doc.pages[0]
    words = [w.text for w in cover.words]
    assert words[:4] == ["ACME", "LIMITED", "RED", "HERRING"]
    for w in cover.words:
        x0, y0, x1, y1 = w.bbox
        assert 0 <= x0 < x1 <= cover.width
        assert 0 <= y0 < y1 <= cover.height


def test_word_box_matches_where_it_was_drawn(doc: ParsedDoc) -> None:
    red = next(w for w in doc.pages[0].words if w.text == "RED")
    assert red.bbox[0] == pytest.approx(72, abs=0.5)
    assert red.bbox[1] < 120 < red.bbox[3]  # baseline at y = 120 lies inside the box


def test_font_size_and_bold(doc: ParsedDoc) -> None:
    by_text = {w.text: w for w in doc.pages[0].words}
    assert by_text["PROSPECTUS"].bold is True
    assert by_text["PROSPECTUS"].font_size == pytest.approx(20, abs=0.5)
    assert by_text["Fresh"].bold is False
    assert by_text["Fresh"].font_size == pytest.approx(10, abs=0.5)


def test_rupee_sign_and_placeholder_survive(doc: ParsedDoc) -> None:
    text = doc.pages[0].text
    assert "₹ 800.00 crore" in text
    assert "[●]" in text


def test_repeated_header_is_stripped_from_text_but_words_are_kept(doc: ParsedDoc) -> None:
    assert "ACME LIMITED" not in doc.pages[1].text
    assert "Body text on page 2" in doc.pages[1].text
    assert any(w.text == "ACME" for w in doc.pages[1].words)  # highlight boxes still exist


def test_printed_page_numbers_from_footer(doc: ParsedDoc) -> None:
    assert [p.printed_page for p in doc.pages] == [None, "2", "3", None]
    assert "\n2" not in doc.pages[1].text.rstrip()[-3:]  # footer number is boilerplate


def test_scanned_page_is_flagged(doc: ParsedDoc) -> None:
    assert [p.is_scanned for p in doc.pages] == [False, False, False, True]
    assert doc.pages[3].words == []


def test_parsed_doc_round_trips_json(doc: ParsedDoc) -> None:
    assert ParsedDoc.model_validate_json(doc.model_dump_json()) == doc


def test_render_pages_writes_webp(fixture_pdf: Path, tmp_path: Path) -> None:
    written = render_pages(fixture_pdf, tmp_path, dpi=50, pages=[1, 2])
    assert [p.name for p in written] == ["1.webp", "2.webp"]
    with Image.open(written[0]) as img:
        assert img.format == "WEBP"
        assert img.width == pytest.approx(595 * 50 / 72, abs=2)


# ---------------------------------------------------------------- clean helpers
@pytest.mark.parametrize(
    ("line", "key"),
    [("Page 12 of 600", "page # of #"), ("  ACME   LIMITED ", "acme limited"), ("45", "#")],
)
def test_line_key_masks_digits_and_whitespace(line: str, key: str) -> None:
    assert line_key(line) == key


def test_boilerplate_needs_more_than_half_the_pages() -> None:
    pages = [["HEADER", "a"], ["HEADER", "b"], ["HEADER", "c"], ["other", "d"]]
    assert boilerplate_keys(pages) == {"header"}
    assert boilerplate_keys([["x"], ["y"]]) == set()


@pytest.mark.parametrize(
    ("lines", "expected"),
    [(["12"], "12"), (["xiv"], "xiv"), (["Page 7"], "7"), (["ACME"], None), ([], None)],
)
def test_read_printed_page(lines: list[str], expected: str | None) -> None:
    assert read_printed_page(lines) == expected


def test_is_scanned_page() -> None:
    assert is_scanned_page(n_chars=10, n_images=1) is True
    assert is_scanned_page(n_chars=10, n_images=0) is False
    assert is_scanned_page(n_chars=500, n_images=3) is False
