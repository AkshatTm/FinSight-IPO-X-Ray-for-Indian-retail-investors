"""Row rules, units, page choice and continuation pages on synthetic documents."""

from __future__ import annotations

from decimal import Decimal

import pytest

from finsight.core.schemas import Money, Page, ParsedDoc, Section, Word
from finsight.summary import clean_label, extract_summary, values_by_source
from finsight.summary.financials import RULES, summary_pages

COLS = (230.0, 310.0, 390.0)


def _w(text: str, x0: float, y: float, x1: float | None = None) -> Word:
    return Word(
        text=text, bbox=(x0, y, x1 if x1 is not None else x0 + 4 * len(text), y + 9),
        font_size=8, bold=False,
    )  # fmt: skip


def _label(text: str, y: float) -> list[Word]:
    out, x = [], 40.0
    for part in text.split():
        out.append(_w(part, x, y))
        x += 4 * len(part) + 3
    return out


def _row(text: str, values: list[str], y: float) -> list[Word]:
    cells = [_w(v, r - 5 * len(v), y, r) for v, r in zip(values, COLS, strict=True)]
    return [*_label(text, y), *cells]


def _header(unit: str | None = "(₹ in million)", y: float = 100) -> list[Word]:
    words = [_w(unit, 300, y - 12)] if unit else []
    for x, year in zip(COLS, ("2025", "2024", "2023"), strict=True):
        words += [_w("Fiscal", x - 50, y), _w(year, x - 22, y)]
    return words


def _page(n: int, words: list[Word]) -> Page:
    return Page(number=n, width=595, height=842, words=words, text="", is_scanned=False)


def _doc(pages: dict[int, list[Word]], n_pages: int = 60) -> ParsedDoc:
    return ParsedDoc(
        ipo_id="synthetic", doc_type="rhp", source_path="x.pdf", n_pages=n_pages,
        pages=[_page(n, pages.get(n, [])) for n in range(1, n_pages + 1)], sha256="0" * 64,
    )  # fmt: skip


def _sections(**spans: tuple[int, int]) -> list[Section]:
    return [
        Section(id=k, title=k, start_page=a, end_page=b, method="toc", confidence=1.0)
        for k, (a, b) in spans.items()
    ]


SUMMARY_ROWS = [
    ("Revenue from operations", ["300.00", "200.00", "100.00"]),
    ("Restated profit/(loss) for the year", ["30.00", "(20.00)", "(10.00)"]),
    ("Net worth", ["90.00", "60.00", "50.00"]),
    ("Total borrowings", ["45.00", "-", "[●]"]),
]


def _summary_page(rows: list[tuple[str, list[str]]] = SUMMARY_ROWS) -> list[Word]:
    words = _header()
    for k, (label, values) in enumerate(rows):
        words += _row(label, values, 130 + 15 * k)
    return words


@pytest.mark.parametrize(
    ("key", "label", "ok"),
    [
        ("revenue", "Revenue from operations", True),
        ("revenue", "Revenue from operations growth (%)", False),
        ("profit_after_tax", "Restated profit/(loss) for the year", True),
        ("profit_after_tax", "Restated loss before tax", False),
        ("profit_after_tax", "Profit on sale of property, plant and equipment", False),
        ("profit_after_tax", "Loss on fair value measurement of financial liabilities", False),
        ("profit_after_tax", "Profit after tax for the year from continuing operations", False),
        ("profit_after_tax", "Profit after tax", True),
        ("net_worth", "Net Worth (3)", True),
        ("net_worth", "Return on net worth (%)", False),
        ("net_worth", "Total equity", True),
        ("net_worth", "Total equity and liabilities", False),
        ("total_borrowings", "Total borrowings", True),
        ("total_borrowings", "Total borrowings / total equity", False),
        ("operating_cash_flow", "Net cash used in operating activities", True),
        ("operating_cash_flow", "Net cashflows from operating activities", True),
        ("operating_cash_flow", "Cash generated from operations", False),
        ("operating_cash_flow", "A. Cash flows from operating activities before tax", False),
    ],
)
def test_row_rules(key: str, label: str, ok: bool) -> None:
    assert any(r.match(clean_label(label)) for r in RULES[key]) is ok


def test_reads_summary_values_and_statuses() -> None:
    doc = _doc({30: _summary_page()})
    s = extract_summary(doc, _sections(summary=(28, 33), risk_factors=(40, 59)), subsections={})
    assert s.currency_unit == "₹ in million"
    revenue = [v.value.value_inr for v in s.revenue if isinstance(v.value, Money)]
    assert revenue == [Decimal("300000000.00"), Decimal("200000000.00"), Decimal("100000000.00")]
    assert [v.period for v in s.profit_after_tax] == ["latest", "latest-1", "latest-2"]
    assert s.total_borrowings is not None
    assert s.total_borrowings.status == "found"
    # Operating cash flow is not in this summary and there are no cash-flow pages.
    assert {v.status for v in s.operating_cash_flow} == {"not_found"}


def test_dash_is_a_stated_zero_and_placeholder_is_kept() -> None:
    rows = [*SUMMARY_ROWS[:3], ("Total borrowings", ["-", "[●]", "1.00"])]
    s = extract_summary(
        _doc({30: _summary_page(rows)}), _sections(summary=(28, 33)), subsections={}
    )
    assert s.total_borrowings is not None
    assert isinstance(s.total_borrowings.value, Money)
    assert s.total_borrowings.value.value_inr == 0


def test_summary_window_before_risk_factors_when_section_is_missing() -> None:
    assert summary_pages(_sections(risk_factors=(45, 90))) == list(range(5, 45))
    assert summary_pages(_sections(summary=(20, 25))) == list(range(20, 26))
    doc = _doc({30: _summary_page()})
    s = extract_summary(doc, _sections(risk_factors=(45, 59)), subsections={})
    assert s.revenue[0].status == "found"


def test_continuation_page_joins_the_summary_table() -> None:
    first = _summary_page(SUMMARY_ROWS[:3])
    second = _row("Total borrowings", ["45.00", "40.00", "35.00"], 130)  # no unit, no header
    second += _row("Long term borrowings", ["5.00", "4.00", "3.00"], 145)
    second += _row("Short term borrowings", ["40.00", "36.00", "32.00"], 160)
    doc = _doc({30: first, 31: second})
    s = extract_summary(doc, _sections(summary=(28, 33)), subsections={})
    assert s.total_borrowings is not None
    assert s.total_borrowings.status == "found"
    assert s.total_borrowings.evidence is not None
    assert s.total_borrowings.evidence.page == 31


def test_unit_in_the_row_label_wins_over_a_bare_currency() -> None:
    rows = [("Revenue from operations (₹ in million)", ["3.00", "2.00", "1.00"]), *SUMMARY_ROWS[1:]]
    words = [w for w in _summary_page(rows) if w.text != "(₹ in million)"]
    words.append(_w("(₹)", 300, 88))
    s = extract_summary(_doc({30: words}), _sections(summary=(28, 33)), subsections={})
    revenue = s.revenue[0].value
    assert isinstance(revenue, Money)
    assert revenue.value_inr == Decimal("3000000.00")
    pat = s.profit_after_tax[0].value
    assert isinstance(pat, Money)
    assert pat.value_inr == Decimal("30.00")  # the table says rupees


def test_without_a_unit_nothing_is_read() -> None:
    words = [w for w in _summary_page() if w.text != "(₹ in million)"]
    s = extract_summary(_doc({30: words}), _sections(summary=(28, 33)), subsections={})
    assert s.currency_unit == ""
    assert {v.status for v in s.revenue} == {"not_found"}


def test_values_by_source_compares_summary_and_statements() -> None:
    sfi = _header() + _row("Revenue from operations", ["300.00", "200.00", "100.00"], 130)
    sfi += _row("Other income", ["1.00", "1.00", "1.00"], 145)
    sfi += _row("Profit for the year", ["30.00", "(20.00)", "(10.00)"], 160)
    doc = _doc({30: _summary_page(), 50: sfi})
    by = values_by_source(
        doc, _sections(summary=(28, 33), summary_financial_information=(50, 52)), "d"
    )
    assert by["revenue:latest"] == {
        "summary": Decimal("300000000.00"),
        "sfi": Decimal("300000000.00"),
    }
    assert "sfi" not in by["net_worth"]
