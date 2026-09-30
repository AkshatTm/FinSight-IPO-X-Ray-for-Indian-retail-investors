"""Objects of the Offer: read the proceeds table that ``parse.tables`` found (B4, table extractor).

The table lists each purpose and its amount ("Capital expenditure ... 9,272"). The unit comes from
the table header ("₹ in million") and stays in the amount text, so nothing is rescaled here.
"""

from __future__ import annotations

import re

from finsight.core.schemas import Candidate, FieldSpec, ParsedDoc, Section, Table, TableValue
from finsight.normalize import parse_amount
from finsight.parse import is_pure_ofs, table_rows

_NUMBERING = re.compile(r"^\s*\(?\d{1,3}[.)]\s*")
# rows of the gross-to-net bridge and the total line are not purposes
_NOT_A_PURPOSE = re.compile(
    r"^(?:less\b|gross\b|net\b|total\b|particulars\b)|\b(?:offer expenses|net proceeds)\b",
    re.IGNORECASE,
)


OBJECTS_TEXT_PAGES = 3  # the pure-OFS sentence sits on the first pages of the section
_PURPOSE_WORDS = re.compile(
    r"\b(?:capital expenditure|expenditure|repayment|pre-?payment|investment|funding|acquisition|"
    r"general corporate|working capital|brand|marketing|technology|research|lease)\b",
    re.IGNORECASE,
)
_GENERAL = re.compile(r"general corporate", re.IGNORECASE)
_NET_HEADER = re.compile(r"net proceeds", re.IGNORECASE)


def _rank(table: Table, rows: list[list[str]]) -> tuple[int, int, int, int]:
    """The utilisation table: has a general-corporate row, says "Net Proceeds" in its header,
    reads like purposes, and is long. The project-cost and offer-expense tables lose."""
    header = " ".join(c.text for c in table.cells if c.row < 3)
    return (
        int(any(_GENERAL.search(r[0]) for r in rows)),
        int(bool(_NET_HEADER.search(header))),
        sum(bool(_PURPOSE_WORDS.search(r[0])) for r in rows),
        len(rows),
    )


def objects_pure_ofs(doc: ParsedDoc, sections: list[Section]) -> bool:
    """The Objects section says the company gets no proceeds (a pure offer for sale)."""
    section = next((s for s in sections if s.id == "objects_of_the_offer"), None)
    if section is None:
        return False
    last = min(section.end_page, section.start_page + OBJECTS_TEXT_PAGES - 1)
    text = "\n".join(doc.pages[n - 1].text for n in range(section.start_page, last + 1))
    return is_pure_ofs(text)


_SERIAL = re.compile(r"^\(?\d{1,3}[.)]?$|^[ivx]+\.?$", re.IGNORECASE)
_TRAILING_NOTES = re.compile(r"(?:\s*(?:\(\d{1,2}\)|[*^#]))+\s*$")  # "purposes (1)", "Total *"


def _purpose_rows(table: Table) -> list[list[str]]:
    scale = table.header_scale
    rows: list[list[str]] = []
    for cells in table_rows(table):
        if len(cells) > 2 and _SERIAL.match(cells[0].strip()):
            cells = cells[1:]  # the first column is only the serial number
        label = _TRAILING_NOTES.sub("", _NUMBERING.sub("", cells[0]).strip()).strip()
        if not label or parse_amount(label) is not None or _NOT_A_PURPOSE.search(label):
            continue
        for cell in cells[1:]:
            amount = parse_amount(cell, scale)
            if amount is not None and getattr(amount, "kind", "") in ("money", "placeholder"):
                text = cell if not scale else f"{cell} ({scale})"
                rows.append([label, text])
                break
    return rows


class TableExtractor:
    """Implements ``core.interfaces.Extractor`` for ``objects_of_offer`` only."""

    name = "table"

    def extract(
        self,
        doc: ParsedDoc,
        sections: list[Section],
        tables: list[Table],
        field: FieldSpec,
    ) -> list[Candidate]:
        if field.id != "objects_of_offer" or objects_pure_ofs(doc, sections):
            return []
        best: tuple[Table, list[list[str]]] | None = None
        for table in tables:
            if table.section_id != "objects_of_the_offer":
                continue
            rows = _purpose_rows(table)
            if rows and (best is None or _rank(table, rows) > _rank(best[0], best[1])):
                best = (table, rows)
        if best is None:
            return []
        table, rows = best
        return [
            Candidate(
                field_id=field.id,
                extractor=self.name,
                doc_type=doc.doc_type,
                raw=" | ".join(f"{label} :: {amount}" for label, amount in rows),
                value=TableValue(columns=["Purpose", "Amount"], rows=rows),
                page=min(table.pages),
                score=0.9,
            )
        ]
