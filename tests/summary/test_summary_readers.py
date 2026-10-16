"""C3.1b readers on synthetic pages shaped like the dev RHPs' tables and sentences."""

from __future__ import annotations

from decimal import Decimal

import pytest

import finsight.summary as summary_pkg
from finsight.core.schemas import Count, Money, Page, ParsedDoc, Percent, Section, Word
from finsight.summary.anchored import split_line
from finsight.summary.customers import extract_customers
from finsight.summary.holdings import identifiable, pledged
from finsight.summary.layout import Line
from finsight.summary.litigation import extract_litigation
from finsight.summary.objects import general_purposes
from finsight.summary.peers import extract_peers

DOC = "synthetic-2025"


def _w(text: str, x0: float, y: float, x1: float | None = None) -> Word:
    return Word(
        text=text, bbox=(x0, y, x1 if x1 is not None else x0 + 4 * len(text), y + 8),
        font_size=8, bold=False,
    )  # fmt: skip


def _words(text: str, x: float, y: float) -> list[Word]:
    out = []
    for part in text.split():
        out.append(_w(part, x, y))
        x += 4 * len(part) + 3
    return out


def _doc(words: list[Word], text: str, section: str) -> tuple[ParsedDoc, list[Section]]:
    page = Page(number=1, width=595, height=842, words=words, text=text, is_scanned=False)
    doc = ParsedDoc(
        ipo_id=DOC, doc_type="rhp", source_path="x.pdf", n_pages=1, pages=[page], sha256="0"
    )
    sec = Section(id=section, title=section, start_page=1, end_page=1, method="toc", confidence=1)
    return doc, [sec]


# ------------------------------------------------------------------------- cells
def test_cells_split_whole_values_and_keep_marks() -> None:
    line = Line(
        top=0,
        words=[
            *_words("Against our Company", 60, 0),
            _w("9", 160, 0, 164), _w("^^", 165, 0, 171),
            _w("N.A.", 280, 0, 298), _w("USD", 300, 0, 312), _w("2", 314, 0, 318),
            _w("million", 320, 0, 348),
        ],
    )  # fmt: skip
    label, cells = split_line(line)
    assert " ".join(w.text for w in label) == "Against our Company"
    assert [c.text for c in cells] == ["9 ^^", "N.A.", "USD 2 million"]


# ------------------------------------------------------------------------- litigation
def _litigation_words(total_row: bool = False) -> list[Word]:
    words = [
        *_words("Name", 60, 100), _w("Criminal", 150, 100), _w("Tax", 220, 100),
        _w("Aggregate", 300, 100),
        _w("proceedings", 145, 110), _w("proceedings", 215, 110), _w("amount", 300, 110),
        _w("(₹", 335, 110), _w("in", 347, 110), _w("million)", 357, 110),
        *_words("By the Company", 60, 130), _w("Nil", 155, 130), _w("Nil", 225, 130),
        _w("Nil", 330, 130),
        *_words("Against the Company", 60, 145), _w("2", 160, 145), _w("3", 228, 145),
        _w("150.50", 320, 145),
        *_words("Against Subsidiaries", 60, 160), _w("Nil", 155, 160), _w("1", 228, 160),
        _w("USD", 300, 160), _w("5", 314, 160), _w("million", 320, 160),
    ]  # fmt: skip
    if total_row:
        words += [
            _w("Total", 60, 175),
            _w("2", 160, 175),
            _w("4", 228, 175),
            _w("160.00", 316, 175),
        ]
    return words


def test_litigation_sums_rows_in_rupees() -> None:
    doc, secs = _doc(_litigation_words(), "summary of outstanding litigation criminal", "summary")
    lit = extract_litigation(doc, secs, DOC)
    criminal, amount = lit["criminal_cases"], lit["amount_total"]
    assert isinstance(criminal.value, Count)
    assert (criminal.status, criminal.value.value) == ("found", 2)
    assert isinstance(amount.value, Money)
    assert amount.value.value_inr == Decimal("150500000")
    assert amount.evidence is not None
    assert "left out: Against Subsidiaries: USD 5 million" in (amount.evidence.sentence or "")


def test_litigation_uses_a_printed_total_row() -> None:
    doc, secs = _doc(_litigation_words(True), "criminal", "summary")
    amount = extract_litigation(doc, secs, DOC)["amount_total"]
    assert isinstance(amount.value, Money)
    assert amount.value.value_inr == Decimal("160000000")


def test_all_nil_criminal_column_is_a_stated_zero() -> None:
    words = [w for w in _litigation_words() if w.bbox[1] != 145]  # drop the row with figures
    doc, secs = _doc(words, "criminal", "summary")
    criminal = extract_litigation(doc, secs, DOC)["criminal_cases"]
    assert criminal.status == "stated_zero"
    assert isinstance(criminal.value, Count)
    assert criminal.value.value == 0


def test_no_litigation_table_gives_nothing() -> None:
    doc, secs = _doc(_words("No table here", 60, 100), "nothing", "summary")
    assert extract_litigation(doc, secs, DOC) == {}


# ------------------------------------------------------------------------- peers
def test_peers_from_words() -> None:
    words = [
        *_words("Name of the company", 60, 100), _w("Face", 170, 100), _w("P/E", 220, 100),
        _w("EPS", 270, 100), _w("RoNW", 320, 100), _w("NAV", 370, 100),
        _w("value", 170, 110), _w("(Basic)", 265, 110), _w("(%)", 322, 110),
        *_words("Our Company", 60, 130), _w("10", 175, 130), _w("[●]", 222, 130),
        _w("5.00", 270, 130), _w("12.5%", 320, 130), _w("40.00", 370, 130),
        *_words("Peer A Limited", 60, 145), _w("2", 178, 145), _w("25.50", 218, 145),
        _w("10.00", 270, 145), _w("(3.5%)", 318, 145), _w("80.00", 370, 145),
    ]  # fmt: skip
    doc, secs = _doc(words, "P/E EPS peers", "basis_for_offer_price")
    peers = extract_peers(doc, secs, DOC)
    assert [(p.name, p.is_issuer) for p in peers] == [
        ("Our Company", True), ("Peer A Limited", False)
    ]  # fmt: skip
    ours, peer = peers
    assert (ours.pe, ours.eps, ours.ronw, ours.nav) == (
        None, Decimal("5.00"), Decimal("12.5"), Decimal("40.00")
    )  # fmt: skip
    assert (peer.pe, peer.ronw) == (Decimal("25.50"), Decimal("-3.5"))
    assert peer.evidence is not None
    assert peer.evidence.sentence == "Peer A Limited: pe 25.50; eps 10.00; ronw (3.5%); nav 80.00"


# ------------------------------------------------------------------------- holdings
def _table_one(promoter_pct: str) -> list[Word]:
    return [
        *_words("Category of shareholder", 20, 100), *_words("Number of shares", 150, 100),
        _w("pledged", 380, 100), _w("or", 410, 100), _w("otherwise", 420, 100),
        _w("encumbered", 458, 100, 498),
        _w("No.", 365, 112), _w("(a)", 380, 112),
        _w("As", 446, 112), _w("a", 458, 112), _w("%", 464, 112), _w("of", 470, 112),
        _w("total", 480, 112),
        _w("(A)", 20, 130), *_words("Promoter and Promoter Group", 40, 130), _w("3", 160, 130),
        _w("1,000", 185, 130), _w("400", 365, 130),
        _w(promoter_pct, 460 if promoter_pct == "-" else 450, 130),  # dashes sit centred
        _w("(B)", 20, 145), _w("Public", 40, 145), _w("100", 160, 145), _w("9,000", 185, 145),
        _w("-", 370, 145), _w("-", 460, 145),
    ]  # fmt: skip


def test_pledged_share_from_table_one_column_xiii_b() -> None:
    doc, secs = _doc(_table_one("40.00%"), "(A) encumbered shareholder", "capital_structure")
    v = pledged(doc, secs, DOC)
    assert v is not None
    assert isinstance(v.value, Percent)
    assert (v.status, v.value.value) == ("found", Decimal("40.00"))
    assert (v.evidence.sentence if v.evidence else "").startswith("[shareholding pattern, XIII(b)]")


def test_dash_in_table_one_is_a_stated_zero() -> None:
    doc, secs = _doc(_table_one("-"), "(A) encumbered shareholder", "capital_structure")
    v = pledged(doc, secs, DOC)
    assert v is not None
    assert v.status == "stated_zero"


def test_none_pledged_sentence_is_a_stated_zero() -> None:
    text = "As on date, none of the Equity Shares held by our Promoters are pledged or encumbered."
    doc, secs = _doc([], text, "capital_structure")
    v = pledged(doc, secs, DOC)
    assert v is not None
    assert v.status == "stated_zero"
    assert v.evidence is not None
    assert "none of the Equity Shares held by our Promoters are pledged" in (
        v.evidence.sentence or ""
    )


def test_no_identifiable_promoter() -> None:
    no, _ = _doc([], "Our Company does not have an identifiable promoter.", "summary")
    yes, _ = _doc([], "Our Promoters are Tarun Mehta and Swapnil Jain.", "summary")
    assert (identifiable(no), identifiable(yes)) == (False, True)


# ------------------------------------------------------------------------- objects
def _objects(gcp: str) -> list[Word]:
    return [
        _w("(₹", 400, 90), _w("in", 412, 90), _w("million)", 422, 90),
        _w("Particulars", 60, 100), _w("Amount", 400, 100),
        *_words("Gross Proceeds", 60, 115), _w("1,000.00", 400, 115),
        *_words("1. Repayment of borrowings", 60, 130), _w("600.00", 404, 130),
        *_words("2. General corporate purposes", 60, 145), _w(gcp, 404, 145),
        *_words("Net Proceeds", 60, 160), _w("800.00", 404, 160),
    ]  # fmt: skip


def test_general_purposes_share_of_gross_proceeds() -> None:
    doc, secs = _doc(_objects("200.00"), "general corporate purposes", "objects_of_the_offer")
    v = general_purposes(doc, secs, DOC)
    assert v is not None
    assert isinstance(v.value, Percent)
    assert (v.status, v.value.value) == ("found", Decimal("20.00"))
    assert (v.evidence.sentence if v.evidence else "").startswith(
        "[computed: 2. General corporate purposes 200.00 / Gross Proceeds 1,000.00]"
    )


def test_general_purposes_placeholder_and_cap_sentence() -> None:
    words = [
        *_objects("[●](2)"),
        *_words("The amount for general corporate purposes shall not exceed 25%", 60, 200),
    ]
    doc, secs = _doc(words, "general corporate purposes", "objects_of_the_offer")
    v = general_purposes(doc, secs, DOC)
    assert v is not None
    assert (v.status, v.value) == ("placeholder", None)


# ------------------------------------------------------------------------- customers
def test_customer_shares_take_the_latest_fiscal_year() -> None:
    words = [
        _w("Particulars", 60, 100),
        _w("Fiscal", 200, 100), _w("2025", 228, 100),
        _w("Fiscal", 280, 100), _w("2024", 308, 100),
        _w("Fiscal", 360, 100), _w("2023", 388, 100),
        *_words("Largest customer", 60, 115),
        _w("12.0%", 215, 115), _w("11.5%", 295, 115), _w("10.1%", 375, 115),
        *_words("Top 10 customers", 60, 130),
        _w("45.1%", 215, 130), _w("40.2%", 295, 130), _w("38.0%", 375, 130),
    ]  # fmt: skip
    doc, secs = _doc(words, "Largest customer Top 10 customers", "risk_factors")
    top1, top10 = extract_customers(doc, secs, DOC)
    assert top1 is not None
    assert top10 is not None
    assert isinstance(top1.value, Percent)
    assert isinstance(top10.value, Percent)
    assert (top1.value.value, top10.value.value) == (Decimal("12.0"), Decimal("45.1"))
    assert top10.period == "latest"


# ------------------------------------------------------------------------- guard
def test_a_failing_reader_leaves_only_its_field_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_: object) -> None:
        raise RuntimeError("reader bug")

    monkeypatch.setattr(summary_pkg, "extract_litigation", boom)
    doc, secs = _doc(_objects("[●]"), "general corporate purposes", "objects_of_the_offer")
    s = summary_pkg.extract_summary(doc, secs, DOC)
    assert s.litigation == {}
    assert s.general_purposes_pct is not None
    assert s.general_purposes_pct.status == "placeholder"
