"""Build the X-Ray of one IPO: one selected value per field, with evidence and consistency checks.

The X-Ray is what the UI shows as the fact sheet. Each field carries the chosen candidate (value,
page, extractor), every candidate from both documents (so the UI can show the RHP ``[●]`` beside
the Prospectus value), a verdict with a plain-English reason, and the consistency checks that
involve it. A failed consistency check is reported in ``checks``; the field verdict only says
whether the extractors agree (``extractors_disagree`` / ``placeholder`` / ``not_in_document``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from finsight.core.schemas import (
    Candidate,
    CheckResult,
    DocType,
    FieldResult,
    FieldSpec,
    Money,
    Placeholder,
    Value,
    XRay,
)
from finsight.extract.fields import load_fields
from finsight.extract.select import best_real, select_field
from finsight.verify import check_consistency

MAX_CANDIDATES = 8  # per field in the X-Ray, best first, at least one per document
CONSISTENCY_FIELDS = ("fresh_issue_size", "ofs_amount", "total_issue_size")


@dataclass
class DocInputs:
    """What the extractors found in one document, plus what the parser learned about it."""

    candidates: dict[str, list[Candidate]] = field(default_factory=dict)  # by field id
    pure_ofs: bool = False
    missing_sections: list[str] = field(default_factory=list)


def _shortlist(candidates: list[Candidate]) -> list[Candidate]:
    ranked = sorted(candidates, key=lambda c: (-c.score, c.page))
    keep = ranked[:MAX_CANDIDATES]
    for doc in ("rhp", "prospectus"):
        best = next((c for c in ranked if c.doc_type == doc), None)
        if best is not None and best not in keep:
            keep[-1] = best
    return sorted(keep, key=lambda c: (-c.score, c.page))


def _consistency_value(
    spec: FieldSpec, chosen: Candidate | None, by_doc: dict[DocType, list[Candidate]]
) -> Value | None:
    """The chosen value; when it is blank, the real value the other document shows."""
    if chosen is None:  # nothing chosen (for example a pure offer for sale): do not guess
        return None
    if not isinstance(chosen.value, Placeholder):
        return chosen.value
    other: DocType = "prospectus" if spec.doc == "rhp" else "rhp"
    real = best_real(spec, by_doc.get(other, []))
    if real is not None and isinstance(real.value, Money):
        return real.value
    return chosen.value


def build_xray(
    ipo_id: str,
    company: str,
    docs: dict[DocType, DocInputs],
    built_at: datetime,
    fields: list[FieldSpec] | None = None,
) -> XRay:
    """``fields`` overrides ``fields.yaml`` (the G2 comparison of two extractor choices)."""
    fields = fields or load_fields()
    results: dict[str, FieldResult] = {}
    for spec in fields:
        by_doc: dict[DocType, list[Candidate]] = {
            doc: inputs.candidates.get(spec.id, []) for doc, inputs in docs.items()
        }
        primary = docs.get(spec.doc, DocInputs())
        missing = [s for s in spec.sections if s in primary.missing_sections]
        sel = select_field(spec, by_doc, pure_ofs=primary.pure_ofs, missing_sections=missing)
        results[spec.id] = FieldResult(
            field_id=spec.id,
            chosen=sel.chosen,
            candidates=_shortlist([c for cands in by_doc.values() for c in cands]),
            verdict=sel.verdict,
            reason_code=sel.reason_code,
            reason=sel.reason,
            checks=[],
        )

    specs = {f.id: f for f in fields}

    def value_of(field_id: str) -> Value | None:
        by_doc = {doc: inputs.candidates.get(field_id, []) for doc, inputs in docs.items()}
        return _consistency_value(specs[field_id], results[field_id].chosen, by_doc)

    report = check_consistency(
        fresh=value_of("fresh_issue_size"),
        ofs_amount=value_of("ofs_amount"),
        total=value_of("total_issue_size"),
        pure_ofs=docs.get("rhp", DocInputs()).pure_ofs,
    )
    checks: list[CheckResult] = report.checks
    for field_id in CONSISTENCY_FIELDS:
        results[field_id] = results[field_id].model_copy(update={"checks": list(checks)})
    return XRay(
        ipo_id=ipo_id,
        company=company,
        built_at=built_at,
        fields=[results[f.id] for f in fields],
        derived=report.derived,
    )
