"""B3.2: the peer table, the issuer's P/E, and percentiles among past IPOs."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from finsight.compare import (
    build,
    cell_number,
    compare,
    issuer_pe,
    load_config,
    peer_median_pe,
    peers_from_table,
    percentiles,
)
from finsight.core.schemas import Peer, Table, TableCell
from finsight.storage import LocalStorage, doc_key, get_json

HEADER = [
    "Name of the company",
    "Face value (₹)",
    "Total income (₹ in million)",
    "P/E",
    "EPS (Diluted) (₹)",
    "EPS (Basic) (₹)",
    "RoNW (%)",
    "NAV per equity share (₹)",
]
ROWS = [
    HEADER,
    ["Acme Widgets Limited", "10", "5,210.4", "[●]", "11.80", "12.10", "15.6", "80.25"],
    ["Listed peers", "", "", "", "", "", "", ""],
    ["Beta Industries Ltd*", "2", "12,345.0", "45.6x", "8.10", "8.20", "18.2%", "55.00"],
    ["Gamma Tools Limited", "10", "4,100.0", "N.A.", "(2.30)", "(2.30)", "(4.1)", "40.10"],
    ["Delta Parts Limited", "5", "7,500.0", "30.4", "6.00", "6.05", "12.0", "61.00"],
]


def table(rows: list[list[str]] = ROWS, page: int = 88) -> Table:
    cells = [
        TableCell(
            row=r,
            col=c,
            text=text,
            bbox=(10.0 * c, 20.0 * r, 10.0 * c + 9, 20.0 * r + 9),
            page=page,
        )
        for r, row in enumerate(rows)
        for c, text in enumerate(row)
    ]
    return Table(id="t1", section_id="basis_for_offer_price", pages=[page], cells=cells)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1,234.50", Decimal("1234.50")),
        ("(2.30)", Decimal("-2.30")),
        ("-4.1", Decimal("-4.1")),
        ("45.6x", Decimal("45.6")),
        ("18.2%", Decimal("18.2")),
        ("₹ 10", Decimal("10")),
        ("N.A.", None),
        ("NA", None),
        ("[●]", None),
        ("-", None),
        ("", None),
        ("Not applicable", None),
    ],
)
def test_cell_number(text: str, value: Decimal | None) -> None:
    assert cell_number(text) == value


@given(st.decimals(min_value=-(10**9), max_value=10**9, places=2, allow_nan=False))
def test_cell_number_reads_grouped_and_bracketed_numbers(d: Decimal) -> None:
    text = f"{abs(d):,.2f}"
    assert cell_number(f"({text})" if d < 0 else text) == d


def test_peer_table_rows_issuer_and_basic_eps() -> None:
    peers = peers_from_table(table(), "doc_x", issuer="Acme Widgets Limited")
    assert [p.name for p in peers] == [
        "Acme Widgets Limited",
        "Beta Industries Ltd",
        "Gamma Tools Limited",
        "Delta Parts Limited",
    ]  # the "Listed peers" heading is skipped, footnote marks removed
    acme, beta, gamma, _ = peers
    assert acme.is_issuer
    assert not beta.is_issuer
    assert acme.pe is None  # [●] in an RHP
    assert acme.eps == Decimal("12.10")  # basic, not diluted
    assert (beta.pe, beta.ronw, beta.nav) == (Decimal("45.6"), Decimal("18.2"), Decimal("55.00"))
    assert gamma.pe is None
    assert gamma.eps == Decimal("-2.30")
    assert beta.evidence is not None
    assert beta.evidence.page == 88
    assert beta.evidence.bbox == (0.0, 60.0, 79.0, 69.0)  # the whole row


def test_issuer_found_by_name_or_wording_and_missing_columns() -> None:
    rows = [HEADER, ROWS[3], ["Our Company", "10", "1", "[●]", "3", "3", "9", "20"]]
    peers = peers_from_table(table(rows), "d")
    assert [p.name for p in peers if p.is_issuer] == ["Our Company"]
    no_pe = [["Name of the company", "EPS (₹)"], ["Beta", "8.2"]]
    assert peers_from_table(table(no_pe), "d") == []


def test_issuer_pe_and_peer_median() -> None:
    assert issuer_pe(Decimal("250"), Decimal("12.10")) == Decimal("20.66")
    assert issuer_pe(Decimal("250"), Decimal("-2.3")) is None  # loss: no meaningful P/E
    assert issuer_pe(None, Decimal("1")) is None
    peers = peers_from_table(table(), "d", issuer="Acme Widgets")
    assert peer_median_pe(peers) == Decimal("38.0")  # 45.6 and 30.4; blanks and issuer left out
    assert peer_median_pe([]) is None


CFG = {
    "provisional": True,
    "corpus_n": 120,
    "reference_quantiles": {
        "issue_size_inr": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "ofs_share": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "pe": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    },
}


def test_percentiles_skip_missing_metrics_and_reference() -> None:
    out = percentiles({"issue_size_inr": 55, "ofs_share": None, "insider_price_gap": 3.0}, CFG)
    assert [(p.metric, p.percentile, p.corpus_n) for p in out] == [("issue_size_inr", 55.0, 120)]


def test_compare_fills_issuer_pe_and_its_percentile(tmp_path: Path) -> None:
    peers = peers_from_table(table(), "d", issuer="Acme Widgets")
    result = compare(peers, {"ofs_share": 0.65}, CFG, offer_price=Decimal("250"))
    assert result.peers[0].pe == Decimal("20.66")
    assert peers[0].pe is None  # the input is not changed
    assert {p.metric: p.percentile for p in result.percentiles} == {
        "ofs_share": 65.0,
        "pe": 20.7,
    }
    assert result.provisional is True
    storage = LocalStorage(tmp_path)
    build(storage, "doc_y", peers, {}, Decimal("250"), CFG)
    saved = get_json(storage, doc_key("doc_y", "compare.json"))
    assert saved["peer_median_pe"] == "38.0"
    assert saved["peers"][0]["pe"] == "20.66"


def test_shipped_config_is_provisional_and_complete() -> None:
    cfg = load_config()
    assert cfg["provisional"] is True  # until the corpus run (B3.2b) replaces the placeholders
    assert cfg["corpus_n"] == 0
    for metric in ("issue_size_inr", "ofs_share", "insider_price_gap", "pe"):
        q = cfg["reference_quantiles"][metric]
        assert len(q) == 11
        assert q == sorted(q)


def test_empty_compare() -> None:
    result = compare([], {}, CFG)
    assert result.peers == []
    assert result.percentiles == []
    assert result.peer_median_pe is None
    assert Peer(name="x").evidence is None
