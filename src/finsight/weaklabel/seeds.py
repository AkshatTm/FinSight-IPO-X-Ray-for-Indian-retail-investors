"""Seeds: the values a corpus document states on its cover, read only when unambiguous.

Distant supervision starts from values we can trust without a human. The rules extractor
(Rung 1) reads the cover block; a seed is kept only if (1) the cover pages give exactly one
real value (no ``[●]``, no two different numbers), (2) fresh + OFS = total when all three are
seeds, and (3) it agrees with the dataset's Excel columns where those are filled in.
Everything dropped is counted with its reason, so seed precision can be reported (05 section 3).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from finsight.core.schemas import Count, ListValue, Money, ParsedDoc, Placeholder, Section, Value
from finsight.extract import COVER_PAGES, RulesExtractor, get_field, load_fields, same_value
from finsight.normalize import parse_amount
from finsight.verify import check_consistency

LADDER_FIELDS = [f.id for f in load_fields() if f.ladder]
DropReason = Literal[
    "no_match", "placeholder", "ambiguous", "inconsistent", "excel_disagrees", "not_cover_format"
]
ExcelCheck = Literal["agree", "absent"]

_CRORE = re.compile(r"aggregating\s+up\s+to\s+(?:₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)\s*Cr", re.I)
_SHARES = re.compile(r"^\s*([\d,]+)\s+shares", re.I)
MIN_SEED_SCORE = 0.5  # keeps cover hits; drops half-weight guesses (unknown registrar)
_BARE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*$")


@dataclass(frozen=True)
class Seed:
    field_id: str
    value: Value
    raw: str
    page: int
    excel: ExcelCheck


@dataclass
class SeedReport:
    seeds: dict[str, Seed] = field(default_factory=dict)
    dropped: dict[str, DropReason] = field(default_factory=dict)


def _crore(text: str | None) -> Money | None:
    m = _CRORE.search(text or "")
    value = parse_amount(f"₹ {m.group(1)} crore") if m else None
    return value if isinstance(value, Money) else None


def excel_values(row: Mapping[str, str | None]) -> dict[str, Value]:
    """Ladder-field values from the allow-listed Excel columns (blank cells are skipped)."""
    out: dict[str, Value] = {}
    if total := _crore(row.get("Total Issue Size")):
        out["total_issue_size"] = total
    if fresh := _crore(row.get("Fresh Issue")):
        out["fresh_issue_size"] = fresh
    ofs = row.get("Offer for Sale") or ""
    if amount := _crore(ofs):
        out["ofs_amount"] = amount
    if m := _SHARES.match(ofs):
        count = parse_amount(f"{m.group(1)} shares")
        if isinstance(count, Count):
            out["ofs_shares"] = count
    face = _BARE.match(row.get("Face Value per share") or "")
    if face and isinstance(value := parse_amount(f"₹ {face.group(1)}"), Money):
        out["face_value"] = value
    return out


def find_seeds(
    doc: ParsedDoc, sections: list[Section], excel: Mapping[str, Value] | None = None
) -> SeedReport:
    report = SeedReport()
    rules = RulesExtractor()
    for field_id in LADDER_FIELDS:
        cover = [
            c for c in rules.extract(doc, sections, [], get_field(field_id))
            if c.page <= COVER_PAGES and c.value is not None and c.score >= MIN_SEED_SCORE
        ]  # fmt: skip
        real = [c for c in cover if not isinstance(c.value, Placeholder)]
        if not cover:
            report.dropped[field_id] = "no_match"
            continue
        if not real:
            report.dropped[field_id] = "placeholder"
            continue
        best = real[0]
        assert best.value is not None
        if any(c.value is not None and not same_value(best.value, c.value) for c in real[1:]):
            report.dropped[field_id] = "ambiguous"
            continue
        names = best.value.items if isinstance(best.value, ListValue) else []
        if field_id == "promoters" and not all(i.isupper() for i in names):
            # names are only trusted in the capitalised cover line ("PROMOTERS OF OUR COMPANY:
            # A, B AND C"); mixed-case lists run on into the next sentence too often
            report.dropped[field_id] = "not_cover_format"
            continue
        check: ExcelCheck = "absent"
        if excel and field_id in excel:
            if not same_value(best.value, excel[field_id]):
                report.dropped[field_id] = "excel_disagrees"
                continue
            check = "agree"
        report.seeds[field_id] = Seed(field_id, best.value, best.raw, best.page, check)

    trio = ("fresh_issue_size", "ofs_amount", "total_issue_size")
    if all(f in report.seeds for f in trio):
        result = check_consistency(
            fresh=report.seeds[trio[0]].value,
            ofs_amount=report.seeds[trio[1]].value,
            total=report.seeds[trio[2]].value,
        )
        if result.checks and result.checks[0].status == "contradicted":
            for f in trio:
                del report.seeds[f]
                report.dropped[f] = "inconsistent"
    return report
