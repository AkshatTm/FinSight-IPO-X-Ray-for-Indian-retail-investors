"""Pick one value per field from the extractors' candidates, and say how sure we are.

Rules, then the QA models, each propose candidates. The field's primary extractor
(``fields.yaml``) wins, its fallback stands in when it finds nothing. Other extractors never
override the choice: they can only confirm it ("rules and qa_pretrained agree") or cast doubt
(``extractors_disagree``). A value the document leaves as ``[●]`` is reported as a placeholder,
never replaced by a number a model found elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from finsight.core.schemas import (
    Amount,
    Candidate,
    DocType,
    FieldSpec,
    ListValue,
    Placeholder,
    ReasonCode,
    TableValue,
    TextValue,
    Value,
    Verdict,
)
from finsight.normalize import equal

DOC_NAME = {"rhp": "RHP", "prospectus": "Prospectus"}
NO_PROCEEDS_FIELDS = {"fresh_issue_size", "objects_of_offer"}  # empty in a pure offer for sale
_ORDER = ("rules", "table", "qa_finetuned", "qa_pretrained", "bilstm_crf")


@dataclass(frozen=True)
class Selection:
    chosen: Candidate | None
    verdict: Verdict
    reason_code: ReasonCode
    reason: str


def _compact(text: str) -> str:
    return "".join(text.split()).casefold()


def same_value(a: Value, b: Value) -> bool:
    """Not in conflict: amounts equal by ``normalize.equal``; names ignoring case, one inside the
    other ("KFin Technologies" inside "KFin Technologies Limited"); lists as sets where one
    contains the other (a model that names only some of the managers does not contradict)."""
    if isinstance(a, TextValue) and isinstance(b, TextValue):
        x, y = _compact(a.text), _compact(b.text)
        return bool(x and y) and (x in y or y in x)
    if isinstance(a, ListValue) and isinstance(b, ListValue):
        x_set = {_compact(i) for i in a.items}
        y_set = {_compact(i) for i in b.items}
        return bool(x_set and y_set) and (x_set <= y_set or y_set <= x_set)
    if isinstance(a, TableValue) and isinstance(b, TableValue):
        return {_compact(r[0]) for r in a.rows} == {_compact(r[0]) for r in b.rows}
    if isinstance(a, TextValue | ListValue | TableValue) or isinstance(
        b, TextValue | ListValue | TableValue
    ):
        return False
    return equal(_amount(a), _amount(b))


def _amount(value: Value) -> Amount:
    assert not isinstance(value, TextValue | ListValue | TableValue)
    return value


def _is_blank(candidate: Candidate) -> bool:
    return isinstance(candidate.value, Placeholder)


def best_real(field: FieldSpec, candidates: list[Candidate]) -> Candidate | None:
    """The top candidate of the highest-priority extractor that found a real (non-blank) value."""
    tops = _tops([c for c in candidates if not _is_blank(c)])
    return next((tops[e] for e in _priority(field) if e in tops), None)


def _tops(candidates: list[Candidate]) -> dict[str, Candidate]:
    """The best-scoring candidate of each extractor."""
    best: dict[str, Candidate] = {}
    for c in sorted(candidates, key=lambda c: -c.score):
        best.setdefault(c.extractor, c)
    return best


def _priority(field: FieldSpec) -> list[str]:
    first = [e for e in (field.extractor, field.fallback) if e]
    return first + [e for e in _ORDER if e not in first]


def _page(c: Candidate) -> str:
    return f"p. {c.page}"


def _companion_note(field: FieldSpec, by_doc: dict[DocType, list[Candidate]]) -> str:
    other: DocType = "prospectus" if field.doc == "rhp" else "rhp"
    best = best_real(field, by_doc.get(other, []))
    if best is None:
        return ""
    return f" The {DOC_NAME[other]} shows {best.raw} ({_page(best)})."


def select_field(
    field: FieldSpec,
    by_doc: dict[DocType, list[Candidate]],
    *,
    pure_ofs: bool = False,
    missing_sections: list[str] | None = None,
) -> Selection:
    """The chosen candidate, verdict and reason for one field (primary document first)."""
    candidates = by_doc.get(field.doc, [])
    doc_name = DOC_NAME[field.doc]
    if pure_ofs and field.id in NO_PROCEEDS_FIELDS:  # whatever a model guessed, there is nothing
        return Selection(
            None, "verified", "not_in_document",
            "Pure offer for sale: the company receives no proceeds from the Offer.",
        )  # fmt: skip
    if not candidates:
        if missing_sections:
            return Selection(
                None, "unverifiable", "section_not_found",
                f"Section not found in the {doc_name}: {', '.join(missing_sections)}.",
            )  # fmt: skip
        return Selection(
            None, "unverifiable", "not_in_document", f"No value found in the {doc_name}."
        )

    tops = _tops(candidates)
    name = next(e for e in _priority(field) if e in tops)
    chosen = tops[name]
    if _is_blank(chosen):
        return Selection(
            chosen, "unverifiable", "placeholder",
            f"Left as [●] in the {doc_name} ({_page(chosen)})." + _companion_note(field, by_doc),
        )  # fmt: skip

    confirmed: list[str] = []
    clashes: list[Candidate] = []
    for other in {c.extractor for c in candidates} - {name}:
        mine = [c for c in candidates if c.extractor == other and c.value is not None]
        if chosen.value is None:
            continue
        if any(same_value(chosen.value, c.value) for c in mine if c.value is not None):
            confirmed.append(other)
        else:
            # A different value only counts against the choice when it was read from the same
            # page: a model quoting another page is talking about something else.
            same_page = [c for c in mine if c.page == chosen.page]
            if same_page:
                clashes.append(max(same_page, key=lambda c: c.score))
    if clashes:
        detail = "; ".join(f"{c.extractor} read {c.raw} ({_page(c)})" for c in clashes)
        return Selection(
            chosen, "unverifiable", "extractors_disagree",
            f"{name} read {chosen.raw} ({_page(chosen)}) but {detail}.",
        )  # fmt: skip
    if confirmed:
        agreeing = ", ".join([name, *sorted(confirmed)])
        return Selection(
            chosen, "verified", "verified", f"{agreeing} agree ({_page(chosen)}, {doc_name})."
        )
    return Selection(
        chosen, "verified", "verified", f"Found by {name} in the {doc_name} ({_page(chosen)})."
    )
