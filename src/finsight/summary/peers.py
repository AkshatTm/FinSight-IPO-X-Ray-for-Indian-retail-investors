"""Listed peers (RF11): the "Comparison with listed industry peers" table in Basis for Offer Price.

A ruled table (``parse.extract_tables``) is read with the compare parser
(``compare.peers_from_table``); when the page has no ruled table, which is common, the words are
read with the header-anchored reader. Columns are found by their headers (P/E, basic EPS, RoNW,
NAV); the issuer is the row that names the company or says "our company", else the first row.
A blank, "NA" or ``[●]`` is ``None``: the issuer's P/E is usually blank until the price is set.
"""

from __future__ import annotations

import re
from decimal import Decimal

from finsight.compare import cell_number, peers_from_table
from finsight.core.schemas import Page, PageEvidence, ParsedDoc, Peer, Section, Table
from finsight.summary.anchored import AnchoredTable, cell_box, read_anchored
from finsight.summary.financials import _pages, _section_pages

_PE = r"P\s*/\s*E\b|price\s*/?\s*earnings?|price to earnings"
_EPS = r"\bEPS\b|earnings? per share"
_RONW = r"RoNW|return on net ?worth"
_NAV = r"\bNAV\b|asset value|book value"
_MARKS = re.compile(r"[*^#@†‡+$]+|\(\d{1,2}\)")
_ISSUER = re.compile(r"\bour company\b|\bthe company\b|\bthe issuer\b", re.IGNORECASE)
_SUFFIX = re.compile(r"\b(?:limited|ltd\.?)$", re.IGNORECASE)
_HEADING = re.compile(r"\b(?:peer|listed|group|companies)\b", re.IGNORECASE)
_HINT = re.compile(r"P\s*/\s*E|price\s*/?\s*earning", re.IGNORECASE)


def _clean(name: str) -> str:
    return " ".join(_MARKS.sub(" ", name).split())


def _number(text: str) -> Decimal | None:
    """``cell_number`` with the percent sign dropped first, so "(194%)" reads as -194."""
    return cell_number(text.replace("%", ""))


def _issuer_words(doc_id: str) -> str:
    """ "hexaware-technologies-2025" -> "hexaware": the first word of the IPO id."""
    return re.split(r"[-_ ]", doc_id.lower())[0] if doc_id else ""


def _name(row_label: str, after: str) -> str:
    name = _clean(row_label)
    tail = _clean(after)
    if tail and not _SUFFIX.search(name) and len(tail.split()) <= 3 and not _HEADING.search(tail):
        name = f"{name} {tail}"
    return name


def peers_from_words(table: AnchoredTable, doc_id: str, issuer_hint: str = "") -> list[Peer]:
    """Peers from a header-anchored peer table; ``[]`` without a P/E or EPS column."""
    pe = table.column(_PE)
    eps = table.column(_EPS, "basic")
    if eps is None:
        eps = table.column(_EPS)
    ronw, nav = table.column(_RONW), table.column(_NAV)
    if pe is None and eps is None:
        return []
    cols = {"pe": pe, "eps": eps, "ronw": ronw, "nav": nav}
    peers: list[Peer] = []
    for row in table.rows:
        name = _name(row.label, row.label_after)
        if not re.search(r"[A-Za-z]{3}", name):
            continue
        values = {
            k: _number(row.cells[c].text) if c is not None and c in row.cells else None
            for k, c in cols.items()
        }
        figures = sum(c in row.cells for c in cols.values() if c is not None)
        if figures == 0:
            continue
        low = name.lower()
        is_issuer = bool(_ISSUER.search(low)) or bool(issuer_hint and low.startswith(issuer_hint))
        printed = {k: row.cells[c] for k, c in cols.items() if c is not None and c in row.cells}
        ev = PageEvidence(
            doc_id=doc_id, page=table.page, bbox=cell_box(row, *printed.values()),
            sentence=f"{name}: " + "; ".join(f"{k} {c.text}" for k, c in printed.items()),
        )  # fmt: skip
        peers.append(Peer(name=name, is_issuer=is_issuer, evidence=ev, **values))
    if peers and not any(p.is_issuer for p in peers):
        peers[0].is_issuer = True  # SEBI's format puts the issuer in the first row
    return peers


def _from_ruled(tables: list[Table], doc_id: str, issuer: str) -> list[Peer]:
    for table in tables:
        if peers := peers_from_table(table, doc_id, issuer or None):
            return peers
    return []


def extract_peers(
    doc: ParsedDoc, sections: list[Section], doc_id: str, tables: list[Table] | None = None
) -> list[Peer]:
    """The peer table of Basis for Offer Price (ruled tables first, then words)."""
    hint = _issuer_words(doc.ipo_id or doc_id)
    ruled = [t for t in tables or [] if t.section_id == "basis_for_offer_price"]
    if peers := _from_ruled(ruled, doc_id, hint):
        return peers
    pages: list[Page] = _pages(doc, _section_pages(sections, "basis_for_offer_price", 30))
    for page in pages:
        if not _HINT.search(page.text):
            continue
        table = read_anchored(page, _HINT, require=(_EPS,), min_cells=4)
        if table is None:
            continue
        if peers := peers_from_words(table, doc_id, hint):
            return peers
    return []
