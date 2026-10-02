"""The objects-of-the-offer answer, from the table the X-Ray already read (ADR-053).

"What will the money be used for?" is answered by one table: each purpose with its amount. The
retriever finds boilerplate about "proceeds" first and the table's chunks come in pieces (rows 1-2
on one page, rows 3-5 on the next), so a small model never saw every row with its unit and
answered in prose without numbers. For these questions the chat now leads with one passage built
from the extracted rows: each purpose, its amount and the unit printed in the table header, in
one place. The verifier checks the answer against that text like any other passage; the
passage points at the table's page.

A pure offer for sale has no table: the real passage that says the company receives no proceeds
leads instead.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from finsight.core.schemas import Candidate, Passage, TableValue, XRay
from finsight.parse import is_pure_ofs

FIELD_ID = "objects_of_offer"
SECTION = "objects_of_the_offer"
_AMOUNT = re.compile(r"^(?P<num>.+?)\s*\((?P<scale>[^)]*)\)\s*$")
_UNIT = re.compile(r"\b(million|crore|lakh|billion)\b", re.IGNORECASE)
_DOC_NAME = {"rhp": "RHP", "prospectus": "Prospectus"}


def amount_with_unit(text: str) -> str:
    """``9,272 (₹ in million)`` -> ``₹ 9,272 million``; a placeholder stays ``[●]``."""
    m = _AMOUNT.match(text.strip())
    if m is None:
        return text.strip()
    num, unit = m.group("num").strip(), _UNIT.search(m.group("scale"))
    if "●" in num:
        return f"{num} (not yet fixed in this document)"
    if unit is None:
        return f"₹ {num}"
    return f"₹ {num} {unit.group(1).lower()}"


def _table_candidates(xray: XRay) -> list[Candidate]:
    field = next((f for f in xray.fields if f.field_id == FIELD_ID), None)
    if field is None:
        return []
    found = [field.chosen] if field.chosen else []
    found += [c for c in field.candidates if c not in found]
    return [c for c in found if isinstance(c.value, TableValue) and c.value.rows]


def _pick(candidates: list[Candidate]) -> Candidate | None:
    """The Prospectus table if it has every amount (the RHP prints [●] for some), else the first."""
    complete = [c for c in candidates if "●" not in c.raw]
    if complete:
        return sorted(complete, key=lambda c: c.doc_type != "prospectus")[0]
    return candidates[0] if candidates else None


def table_passage(ipo_id: str, cand: Candidate) -> Passage:
    assert isinstance(cand.value, TableValue)
    where = f"{_DOC_NAME.get(cand.doc_type, cand.doc_type)} page {cand.page}"
    lines = [
        f"Objects of the Offer: how the money will be used (table on {where}, amounts as printed):"
    ]
    for n, (label, amount) in enumerate(cand.value.rows, start=1):
        lines.append(f"{n}. {label}: {amount_with_unit(amount)}")
    return Passage(
        id=f"{ipo_id}:objects-table:{cand.doc_type}",
        ipo_id=ipo_id,
        doc_type=cand.doc_type,
        section_id=SECTION,
        page_start=cand.page,
        page_end=cand.page,
        text="\n".join(lines),
        char_to_bbox=[],
    )


def pure_ofs_passage(ipo_id: str, passages: Sequence[Passage]) -> Passage | None:
    """One short passage for a pure offer for sale, on the page of the real sentence.

    The real passage is long and also mentions expenses and the selling shareholders, and a small
    model then answers "no proceeds" and "not found" in one breath. The short text states only
    what the Objects section says: the company receives nothing.
    """
    rows = [p for p in passages if p.section_id == SECTION and is_pure_ofs(p.text)]
    rows.sort(key=lambda p: (p.doc_type != "prospectus", p.page_start))
    if not rows:
        return None
    real = rows[0]
    where = f"{_DOC_NAME.get(real.doc_type, real.doc_type)} page {real.page_start}"
    return Passage(
        id=f"{ipo_id}:objects-pure-ofs:{real.doc_type}",
        ipo_id=ipo_id,
        doc_type=real.doc_type,
        section_id=SECTION,
        page_start=real.page_start,
        page_end=real.page_start,
        text=f"Objects of the Offer ({where}): the Company will not receive any money from this "
        "Offer. The Offer is entirely an offer for sale, so no money from it will be used by "
        "the Company.",
        char_to_bbox=[],
    )


def objects_passage(xray: XRay, passages: Sequence[Passage]) -> Passage | None:
    """The passage to lead with for a use-of-money question, or ``None`` when there is none."""
    chosen = _pick(_table_candidates(xray))
    if chosen is not None:
        return table_passage(xray.ipo_id, chosen)
    field = next((f for f in xray.fields if f.field_id == FIELD_ID), None)
    if field is not None and field.chosen is None and "Pure offer for sale" in field.reason:
        return pure_ofs_passage(xray.ipo_id, passages)
    return None
