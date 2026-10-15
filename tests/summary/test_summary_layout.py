"""Tables rebuilt from word boxes on synthetic pages (layouts seen in dev RHPs)."""

from __future__ import annotations

from finsight.core.schemas import Page, Word
from finsight.summary import clean_label, read_tables
from finsight.summary.layout import is_nil, is_placeholder, is_value_token, unit_of

COLS = (225.0, 303.0, 373.0)


def _w(text: str, x0: float, y: float, x1: float | None = None) -> Word:
    return Word(
        text=text, bbox=(x0, y, x1 if x1 is not None else x0 + 4 * len(text), y + 9),
        font_size=8, bold=False,
    )  # fmt: skip


def _label(text: str, y: float, x: float = 77) -> list[Word]:
    out = []
    for part in text.split():
        out.append(_w(part, x, y))
        x += 4 * len(part) + 3
    return out


def _values(values: list[str], y: float) -> list[Word]:
    return [_w(v, right - 5 * len(v), y, right) for v, right in zip(values, COLS, strict=True)]


def _page(words: list[Word]) -> Page:
    return Page(number=7, width=595, height=842, words=words, text="", is_scanned=False)


def _summary_page() -> Page:
    words = [
        *_label("Summary of selected financial information derived from the Restated", 340),
        _w("(in", 304, 407), _w("₹", 320, 407), _w("million)", 330, 407),
        *_label("Particulars", 418, x=91),
        _w("Nine", 180, 420), _w("months", 199, 420),
        _w("As", 262, 420), _w("at", 273, 420), _w("and", 284, 420), _w("for", 299, 420),
        _w("the", 318, 430), _w("Financial", 333, 430),
        _w("Year", 335, 440), _w("ended", 355, 440),
        _w("2024", 205, 450), _w("2024", 285, 450), _w("2023", 355, 450),
        *_label("Revenue from", 470), *_values(["15,789", "17,538", "17,809"], 470),
        *_label("operations", 480),
        *_label("Restated loss for the", 495), *_values(["(5,779)", "(10,597)", "(8,645)"], 495),
        *_label("period/year", 505),
        *_label("Earnings per", 515),
        *_label("Net Worth", 525, x=77), _w("(3)", 140, 525, 150),
        *_values(["1,080", "5,459", "6,137"], 525),
        *_label("Total borrowings", 540), *_values(["11,216", "3,149", "4,852"], 541),
        *_label("Lease liabilities", 555), *_values(["-", "[●]", "Nil"], 555),
        *_label("* The Board of Directors in its meeting approved the issuance of bonus", 575),
    ]  # fmt: skip
    return _page(words)


def test_tokens() -> None:
    assert all(is_value_token(t) for t in ["15,789", "(5,779)", "(36)*^", "4^", "-", "[●]", "Nil"])
    assert not any(is_value_token(t) for t in ["2024,", "31,", "₹", "million)", "abc"])
    assert is_nil("—")
    assert is_placeholder("[●]")
    assert not is_nil("0")


def test_reads_rows_columns_unit_and_headers() -> None:
    (table,) = read_tables(_summary_page())
    assert table.page == 7
    assert table.unit == "₹ in million"
    assert [round(c.right) for c in table.columns] == [225, 303, 373]
    assert table.columns[0].header == "Nine months 2024"
    # "As at and for" is centred over the second and third columns: both get it.
    assert table.columns[1].header == "As at and for 2024"
    assert table.columns[2].header == "As at and for the Financial Year ended 2023"
    labels = [clean_label(r.labels()[0]) for r in table.rows]
    assert labels == [
        "revenue from operations",
        "restated loss for the period/year",
        "net worth",
        "total borrowings",
        "lease liabilities",
    ]
    assert {k: w.text for k, w in table.rows[3].cells.items()} == {
        0: "11,216", 1: "3,149", 2: "4,852"
    }  # fmt: skip
    assert {k: w.text for k, w in table.rows[4].cells.items()} == {0: "-", 1: "[●]", 2: "Nil"}


def test_continuation_stops_at_a_capitalised_label() -> None:
    (table,) = read_tables(_summary_page())
    loss = table.rows[1]
    assert loss.label_below == "period/year"  # "Earnings per" starts the next label


def test_footnote_mark_next_to_label_is_not_a_column() -> None:
    (table,) = read_tables(_summary_page())
    assert table.rows[2].label == "Net Worth (3)"
    assert len(table.columns) == 3


def test_label_above_values_line() -> None:
    words = [
        _w("(₹", 300, 90), _w("in", 315, 90), _w("crore)", 330, 90),
        _w("Fiscal", 190, 100), _w("2025", 205, 110),
        _w("Fiscal", 268, 100), _w("2024", 283, 110),
        _w("Fiscal", 338, 100), _w("2023", 353, 110),
        *_label("Net cash generated from", 130),
        *_label("Operating activities (A)", 140),
        *_values(["545.58", "(855.75)", "(2,377.98)"], 141),
        *_label("Net cash used in investing activities", 160),
        *_values(["(1.00)", "(2.00)", "(3.00)"], 160),
    ]  # fmt: skip
    (table,) = read_tables(_page(words))
    assert table.unit == "₹ in crore"
    ocf = table.rows[0]
    assert "net cash generated from operating activities" in [clean_label(x) for x in ocf.labels()]


def test_no_table_on_a_text_page() -> None:
    words = [*_label("The Company had revenue of 1,234 and 5,678 in two years", 100)]
    assert read_tables(_page(words)) == []


def test_unit_sentence_with_a_digit() -> None:
    text = "All amounts are ₹ in millions unless otherwise stated (0 represents amount less than"
    assert unit_of(text) == "₹ in million"
    assert unit_of("(Amount in millions of INR unless otherwise stated)") == "₹ in million"
    assert unit_of("(₹ in lakhs)") == "₹ in lakh"
    assert unit_of("Revenue from operations") is None


def _three_columns(header_y: float = 100) -> list[Word]:
    return [
        _w("(₹", 300, header_y - 10), _w("in", 315, header_y - 10),
        _w("million)", 330, header_y - 10),
        # "Fiscal 2025" straddles the first two columns but names only the first.
        _w("Fiscal", 190, header_y), _w("2025", 217, header_y),
        _w("Fiscal", 262, header_y), _w("2024", 289, header_y),
        _w("Fiscal", 335, header_y), _w("2023", 362, header_y),
    ]  # fmt: skip


def test_year_phrases_go_to_one_column_in_reading_order() -> None:
    words = [
        *_three_columns(),
        *_label("Revenue from operations", 130), *_values(["10.00", "9.00", "8.00"], 130),
        *_label("Profit for the year", 145), *_values(["1.00", "2.00", "3.00"], 145),
        *_label("Net worth", 160), *_values(["4.00", "5.00", "6.00"], 160),
    ]  # fmt: skip
    (table,) = read_tables(_page(words))
    assert [c.header for c in table.columns] == ["Fiscal 2025", "Fiscal 2024", "Fiscal 2023"]


def test_second_block_takes_no_figures_as_headers() -> None:
    words = _three_columns()
    for k, y in enumerate(range(130, 190, 15)):
        words += [*_label(f"Item {k}", y), *_values(["1.00", "2.00", "3.00"], y)]
    for text, y in (("Net cash from operating", 300), ("Net cash used", 315), ("Net", 330)):
        words += [*_label(text, y), *_values(["7.00", "8.00", "9.00"], y)]
    first, second = read_tables(_page(words))
    assert first.columns[0].header == "Fiscal 2025"
    assert [c.header for c in second.columns] == ["", "", ""]  # filled from `first` later


def test_clean_label() -> None:
    assert clean_label("IX Restated loss for the period/year (VII - VIII)") == (
        "restated loss for the period/year (vii - viii)"
    )
    assert clean_label("(a) Net Worth (3)*") == "net worth"
    assert clean_label("- Basic earnings per share (₹)") == "basic earnings per share (₹)"
