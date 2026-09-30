from finsight.core.schemas import Candidate, Page, ParsedDoc, Table, TableCell, TableValue
from finsight.extract import TableExtractor, get_field


def make_doc(n: int = 200) -> ParsedDoc:
    page = Page(number=1, width=595, height=842, words=[], text="x", is_scanned=False)
    return ParsedDoc(
        ipo_id="urban-company-2025", doc_type="rhp", source_path="x.pdf", n_pages=n,
        sha256="0", pages=[page],
    )  # fmt: skip


def make_table(rows: list[list[str]], scale: str | None = "₹ in million") -> Table:
    cells = [
        TableCell(row=r, col=c, text=text, bbox=(0, 0, 1, 1), page=164)
        for r, row in enumerate(rows)
        for c, text in enumerate(row)
    ]
    return Table(
        id="t1", section_id="objects_of_the_offer", pages=[164], header_scale=scale, cells=cells
    )


OBJECTS = [
    ["Particulars", "Amount to be funded from Net Proceeds"],
    ["1. Expenditure for new technology development", "1,900.00"],
    ["2. Expenditure for lease payments for our offices", "750.00"],
    ["3. General corporate purposes", "[●]"],
    ["Gross proceeds", "19,000.00"],
    ["Net proceeds", "18,500.00"],
]


def run(table: Table | None, field_id: str = "objects_of_offer") -> list[Candidate]:
    doc = make_doc()
    return TableExtractor().extract(doc, [], [table] if table else [], get_field(field_id))


def run_many(tables: list[Table]) -> list[Candidate]:
    return TableExtractor().extract(make_doc(), [], tables, get_field("objects_of_offer"))


def test_purposes_and_amounts_become_rows() -> None:
    (cand,) = run(make_table(OBJECTS))
    assert isinstance(cand.value, TableValue)
    assert cand.value.rows == [
        ["Expenditure for new technology development", "1,900.00 (₹ in million)"],
        ["Expenditure for lease payments for our offices", "750.00 (₹ in million)"],
        ["General corporate purposes", "[●] (₹ in million)"],
    ]
    assert cand.page == 164
    assert cand.extractor == "table"
    assert " :: " in cand.raw


def test_no_table_or_other_field_gives_nothing() -> None:
    assert run(None) == []
    assert run(make_table(OBJECTS), "registrar") == []


def test_a_table_from_another_section_is_ignored() -> None:
    other = make_table(OBJECTS).model_copy(update={"section_id": "capital_structure"})
    assert run(other) == []


def test_the_table_with_the_most_purposes_wins() -> None:
    bridge = make_table([["Gross proceeds", "19,000.00"], ["Less: Offer expenses", "[●]"]])
    (cand,) = run_many([bridge, make_table(OBJECTS)])
    assert len(cand.value.rows) == 3  # type: ignore[union-attr]


def test_serial_number_column_and_footnote_marks_are_dropped() -> None:
    rows = [
        ["S. No.", "Particulars", "Amount to be funded from Net Proceeds"],
        ["1.", "Capital expenditure for a factory", "9,272"],
        ["2.", "Repayment of borrowings", "400"],
        ["3.", "General corporate purposes (1)(2)", "[●]"],
    ]
    (cand,) = run(make_table(rows))
    assert isinstance(cand.value, TableValue)
    assert [r[0] for r in cand.value.rows] == [
        "Capital expenditure for a factory",
        "Repayment of borrowings",
        "General corporate purposes",
    ]


def test_pure_offer_for_sale_gives_no_objects_table() -> None:
    from finsight.core.schemas import Page, Section

    text = "Our Company will not receive any proceeds from the Offer"
    doc = make_doc().model_copy(
        update={"pages": [Page(number=1, width=1, height=1, words=[], text=text, is_scanned=False)]}
    )
    section = Section(
        id="objects_of_the_offer", title="Objects", start_page=1, end_page=1, method="toc",
        confidence=1.0,
    )  # fmt: skip
    got = TableExtractor().extract(
        doc, [section], [make_table(OBJECTS)], get_field("objects_of_offer")
    )
    assert got == []
