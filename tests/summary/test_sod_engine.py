"""SOD engine (CC-05b / CC-06) on synthetic pages: where readers look, litigation counted from
sections, strengths, ratios and ``SODResult``."""

from __future__ import annotations

from decimal import Decimal

from finsight.core.schemas import (
    Count,
    FinancialSummary,
    Money,
    Page,
    PageEvidence,
    ParsedDoc,
    Section,
    SummaryValue,
    Word,
)
from finsight.summary.derived import ratios
from finsight.summary.litigation_prose import METHOD, criminal_from_sections
from finsight.summary.locate import reader_pages, scan_start, source_of
from finsight.summary.sod import SODResult, build_sod
from finsight.summary.strengths import extract_strengths

DOC = "synthetic-2026"


def _sec(sid: str, start: int, end: int) -> Section:
    return Section(id=sid, title=sid, start_page=start, end_page=end, method="toc", confidence=1)


def _doc(pages: list[Page]) -> ParsedDoc:
    return ParsedDoc(ipo_id=DOC, doc_type="rhp", source_path="x.pdf", n_pages=len(pages),
                     pages=pages, sha256="0")  # fmt: skip


def _text_page(n: int, text: str) -> Page:
    return Page(number=n, width=595, height=842, words=[], text=text, is_scanned=False)


# ------------------------------------------------------------------------- locate
def test_readers_use_the_sod_when_there_is_one() -> None:
    sections = [_sec("summary", 20, 30), _sec("risk_factors", 31, 60),
                _sec("capital_structure", 90, 100)]  # fmt: skip
    assert reader_pages(sections, "holdings") == list(range(20, 31))
    assert source_of(sections, "holdings") == "sod"
    assert scan_start(sections) == 20


def test_without_a_sod_readers_use_their_chapter_then_the_pages_before_risk_factors() -> None:
    sections = [_sec("risk_factors", 50, 70), _sec("capital_structure", 90, 95),
                _sec("outstanding_litigation", 300, 330)]  # fmt: skip
    pages = reader_pages(sections, "holdings")
    assert pages[:6] == list(range(90, 96))
    assert pages[6:] == list(range(10, 50))  # the 40 pages before Risk Factors
    assert reader_pages(sections, "litigation")[:25] == list(range(300, 325))
    assert source_of(sections, "holdings") == "fallback:capital_structure"
    assert source_of(sections, "auditor") == "window"
    assert scan_start(sections) == 50  # the severe scan starts at Risk Factors


# ------------------------------------------------------------------------- litigation prose
_CHAPTER = """OUTSTANDING LITIGATION AND MATERIAL DEVELOPMENTS
I.
Outstanding litigation involving our Company
Criminal proceedings against our Company
Nil
Criminal proceedings by our Company
(i) The Company filed a complaint against a former employee.
(ii) The Company filed a complaint under Section 138 of the NI Act.
Material civil litigation against our Company
(i) A civil suit for damages.
II. Outstanding litigation involving our Subsidiaries
Criminal proceedings against our Subsidiaries
ABC Private Limited
(i) A complaint was filed by a customer.
XYZ Private Limited
(i) A complaint was filed by a customer.
(ii) A complaint was filed by a vendor, alleging cheating, which is
civil in nature.
III. Outstanding litigation involving our Directors
Criminal proceedings against our Directors
Nil
"""


def test_criminal_cases_are_counted_per_party_from_the_chapter_headings() -> None:
    doc = _doc([_text_page(1, _CHAPTER)])
    got = criminal_from_sections(doc, [_sec("outstanding_litigation", 1, 1)], DOC)
    assert got is not None
    assert got.status == "found"
    assert isinstance(got.value, Count)
    assert got.value.value == 5  # company 2 + subsidiaries 1 + 2 + directors 0
    sentence = got.evidence.sentence if got.evidence else ""
    assert METHOD in sentence
    for part in ("company: 2", "subsidiaries: 3", "directors: 0"):
        assert part in sentence


def test_a_criminal_section_without_numbered_items_gives_no_number() -> None:
    text = _CHAPTER.replace(
        "Criminal proceedings against our Directors\nNil",
        "Criminal proceedings against our Directors\nThere is a complaint against a director "
        "which is pending before the magistrate.",
    )
    got = criminal_from_sections(_doc([_text_page(1, text)]),
                                 [_sec("outstanding_litigation", 1, 1)], DOC)  # fmt: skip
    assert got is not None
    assert isinstance(got.value, str)
    assert got.value.startswith("Yes — at least 5")
    assert "directors: not countable" in (got.evidence.sentence if got.evidence else "")


def test_no_criminal_headings_means_nothing_is_counted() -> None:
    doc = _doc([_text_page(1, "OUTSTANDING LITIGATION\nThere are cases of various kinds.")])
    assert criminal_from_sections(doc, [_sec("outstanding_litigation", 1, 1)], DOC) is None
    assert criminal_from_sections(doc, [], DOC) is None


# ------------------------------------------------------------------------- strengths
def _line(text: str, y: float, bold: bool) -> list[Word]:
    out, x = [], 60.0
    for part in text.split():
        out.append(Word(text=part, bbox=(x, y, x + 5 * len(part), y + 9), font_size=10,
                        bold=bold))  # fmt: skip
        x += 5 * len(part) + 4
    return out


def _business_page(lines: list[tuple[str, bool]], n: int = 1) -> Page:
    words: list[Word] = []
    y = 60.0
    for text, bold in lines:
        words += _line(text, y, bold)
        y += 30
    text = "\n".join(t for t, _ in lines)
    return Page(number=n, width=595, height=842, words=words, text=text, is_scanned=False)


def test_strengths_are_the_bold_items_between_the_two_headings() -> None:
    page = _business_page([
        ("OUR BUSINESS", True),
        ("We make cement.", False),
        ("Our Competitive Strengths", True),
        ("Leading market position", True),
        ("We are among the largest makers in India. We grew fast.", False),
        ("Strong balance sheet", True),
        ("Our net debt is low compared with peers.", False),
        ("Our Strategies", True),
        ("Expand capacity", True),
    ])  # fmt: skip
    got = extract_strengths(_doc([page]), [_sec("our_business", 1, 1)])
    assert [(s.heading, s.sentence, s.page) for s in got] == [
        ("Leading market position", "We are among the largest makers in India.", 1),
        ("Strong balance sheet", "Our net debt is low compared with peers.", 1),
    ]


def test_no_strengths_heading_gives_an_empty_list() -> None:
    page = _business_page([("OUR BUSINESS", True), ("Leading position", True), ("Text.", False)])
    assert extract_strengths(_doc([page]), [_sec("our_business", 1, 1)]) == []


# ------------------------------------------------------------------------- ratios
def _money(key: str, inr: str, period: str = "latest", page: int = 5) -> SummaryValue:
    value = Money(value_inr=Decimal(inr), currency="INR", raw=inr, scale_word=None, precision=0)
    return SummaryValue(key=key, value=value, period=period, status="found",
                        evidence=PageEvidence(doc_id=DOC, page=page))  # fmt: skip


def _summary() -> FinancialSummary:
    periods = ("latest", "latest-1", "latest-2")
    return FinancialSummary(
        doc_id=DOC,
        revenue=[
            _money("revenue", v, p) for v, p in zip(("1200", "1000", "0"), periods, strict=True)
        ],
        profit_after_tax=[
            _money("profit_after_tax", v, p)
            for v, p in zip(("120", "-50", "10"), periods, strict=True)
        ],
        operating_cash_flow=[_money("operating_cash_flow", "-30", "latest", 7)],
        total_borrowings=_money("total_borrowings", "300", page=6),
        net_worth=_money("net_worth", "600", page=6),
    )


def test_ratios_show_their_formula_inputs_and_pages() -> None:
    got = {(r.key, r.period): r for r in ratios(_summary())}
    growth = got[("revenue_growth_yoy", "latest")]
    assert (growth.value, growth.unit, growth.status) == (Decimal("20.00"), "%", "computed")
    assert "÷ revenue last year" in growth.formula
    assert growth.pages == [5]
    assert got[("pat_margin", "latest")].value == Decimal("10.00")
    assert got[("pat_margin", "latest-1")].value == Decimal("-5.00")
    de = got[("debt_to_equity", "latest")]
    assert (de.value, de.unit, de.pages) == (Decimal("0.50"), "x", [6])
    cash = got[("operating_cash_flow", "latest")]
    assert (cash.value, cash.status) == (Decimal("-30.00"), "as_printed")


def test_a_ratio_without_a_positive_base_is_not_available_with_the_reason() -> None:
    got = {(r.key, r.period): r for r in ratios(_summary())}
    growth = got[("revenue_growth_yoy", "latest-1")]  # base year revenue is 0
    assert (growth.value, growth.status) == (None, "not_available")
    assert growth.reason == "previous year's revenue is not positive"
    margin = got[("pat_margin", "latest-2")]
    assert margin.reason == "revenue is not positive"
    empty = {(r.key, r.period): r for r in ratios(FinancialSummary(doc_id=DOC))}
    assert empty[("debt_to_equity", "latest")].reason == "total borrowings are missing"


# ------------------------------------------------------------------------- SODResult
def test_build_sod_gathers_the_readers_and_leaves_the_price_band_empty() -> None:
    page = _business_page([("Our Strengths", True), ("Brand", True), ("A known brand.", False),
                           ("Our Strategies", True)], n=1)  # fmt: skip
    doc = _doc([page])
    result = build_sod(doc, [_sec("our_business", 1, 1)], _summary(), DOC)
    assert isinstance(result, SODResult)
    assert result.has_sod is False
    assert result.source["holdings"] == "window"
    assert result.price_band is None
    assert [s.heading for s in result.strengths] == ["Brand"]
    fields = result.fields()
    assert fields["revenue:latest"].status == "found"
    assert fields["net_worth:latest"].status == "found"
    assert fields["net_worth:stub"].status == "not_found"
    assert fields["eps_basic:latest"].status == "not_found"
    assert SODResult.model_validate_json(result.model_dump_json()) == result
