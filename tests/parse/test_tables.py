import importlib.util
from pathlib import Path

import pytest

from finsight.core.schemas import Section
from finsight.parse import parse_pdf
from finsight.parse.tables import (
    detect_header_scale,
    docling_backend,
    extract_tables,
    is_pure_ofs,
    objects_table,
    pymupdf_backend,
    table_rows,
)

OBJECTS = [
    Section(id="objects_of_the_offer", title="OBJECTS OF THE OFFER", start_page=1, end_page=1,
            method="toc", confidence=1.0)
]  # fmt: skip


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(in ₹ million)", "₹ in million"),
        ("(₹ in million, except per share data)", "₹ in million"),
        ("Estimated Amount (in ₹ million)", "₹ in million"),
        ("(₹ million)", "₹ in million"),
        ("(Amount in ₹ crores)", "₹ in crore"),
        ("(₹ in crore)", "₹ in crore"),
        ("(Rs. in lakhs)", "₹ in lakh"),
        ("(Rs in Lacs)", "₹ in lakh"),
        ("(INR in billion)", "₹ in billion"),
        ("(in ₹ bn)", "₹ in billion"),
        ("(in ₹ mn)", "₹ in million"),
        ("(Rupees in thousands)", "₹ in thousand"),
        ("(₹ ’000)", "₹ in thousand"),
        ("Amount (in ₹)", "₹"),
        ("(in US$ million)", "$ in million"),
        ("(in million)", "in million"),
        ("Particulars", None),
        ("Gross Proceeds of the Fresh Issue", None),
        ("1 million Equity Shares", None),  # a count, not a unit header
    ],
)
def test_detect_header_scale(text: str, expected: str | None) -> None:
    assert detect_header_scale(text) == expected


def test_first_scale_in_a_multi_line_header_wins() -> None:
    assert detect_header_scale("Particulars\nEstimated Amount\n(in ₹ million)\n(₹ in crore)") == (
        "₹ in million"
    )


def _extract(pdf: Path, backend=pymupdf_backend):  # type: ignore[no-untyped-def]
    doc = parse_pdf(pdf, "acme-2025", "rhp")
    return extract_tables(pdf, doc, OBJECTS, backend=backend)


def test_pymupdf_backend_reads_a_ruled_table(table_pdf: Path) -> None:
    tables = _extract(table_pdf)
    assert len(tables) == 1
    table = tables[0]
    assert (table.section_id, table.pages, table.id) == (
        "objects_of_the_offer", [1], "rhp:objects_of_the_offer:p1:t0",
    )  # fmt: skip
    assert table_rows(table)[1] == ["Gross Proceeds of the Fresh Issue", "4,720"]
    cell = next(c for c in table.cells if c.text == "4,720")
    x0, y0, x1, y1 = cell.bbox
    assert 380 <= x0 < x1 <= 521  # the amount column
    assert 190 <= y0 < y1 <= 215  # second row, measured from the top of the page


def test_unit_line_above_the_table_sets_the_header_scale(table_pdf: Path) -> None:
    assert _extract(table_pdf)[0].header_scale == "₹ in million"


def test_objects_table_is_the_one_with_net_proceeds(table_pdf: Path) -> None:
    table = objects_table(_extract(table_pdf))
    assert table is not None
    assert table_rows(table)[-1] == ["Net Proceeds", "4,500"]
    assert objects_table([]) is None


def test_sections_outside_the_list_are_skipped(table_pdf: Path) -> None:
    doc = parse_pdf(table_pdf, "acme-2025", "rhp")
    other = [OBJECTS[0].model_copy(update={"id": "risk_factors"})]
    assert extract_tables(table_pdf, doc, other, backend=pymupdf_backend) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Our Company will not receive any proceeds from the Offer. All proceeds ...", True),
        ("Our Company will not receive any proceeds from the Offer (the “Offer Proceeds”)", True),
        ("Our Company will not receive any proceeds from the Offer for Sale and ...", False),
        ("The Offer comprises a Fresh Issue of [●] Equity Shares", False),
    ],
)
def test_is_pure_ofs(text: str, expected: bool) -> None:
    assert is_pure_ofs(text) is expected


@pytest.mark.slow
@pytest.mark.skipif(importlib.util.find_spec("docling") is None, reason="uv sync --group tables")
def test_docling_backend_reads_the_same_table(table_pdf: Path) -> None:
    table = objects_table(_extract(table_pdf, backend=docling_backend))
    assert table is not None
    assert ["Net Proceeds", "4,500"] in table_rows(table)
