"""The X-Ray of one uploaded document (the ``facts`` stage): rules and the Objects table reader.

The curated showcase IPOs are built by ``finsight.pipeline`` from stored candidates; an upload
has one document and no QA model on the worker, so this runs the rule and table extractors in
memory and selects each field's value with the same ``build_xray`` (a ``[●]`` price stays a
placeholder, a missing section is a reason, never a guess).
"""

from __future__ import annotations

from datetime import UTC, datetime

from finsight.core.schemas import Candidate, ParsedDoc, Section, Table, XRay
from finsight.extract.fields import load_fields
from finsight.extract.locate import fill_boxes
from finsight.extract.rules import RulesExtractor
from finsight.extract.table import TableExtractor, objects_pure_ofs
from finsight.extract.xray import DocInputs, build_xray
from finsight.parse import KEY_SECTIONS


def upload_xray(
    doc: ParsedDoc,
    sections: list[Section],
    tables: list[Table],
    ipo_id: str,
    company: str,
    built_at: datetime | None = None,
) -> XRay:
    """Rules + table candidates for every field of one document, selected into an X-Ray.

    A draft RHP (``drhp``) is read as an RHP: its fields name the RHP as their primary document.
    """
    if doc.doc_type == "drhp":
        doc = doc.model_copy(update={"doc_type": "rhp"})
    extractors = {"rules": RulesExtractor(), "table": TableExtractor()}
    fields = load_fields()
    found: dict[str, list[Candidate]] = {}
    for field in fields:
        name = field.extractor if field.extractor in extractors else field.fallback
        extractor = extractors.get(name or "")
        cands = extractor.extract(doc, sections, tables, field) if extractor else []
        found[field.id] = fill_boxes(cands, doc)
    present = {s.id for s in sections}
    inputs = DocInputs(
        candidates=found,
        pure_ofs=objects_pure_ofs(doc, sections),
        missing_sections=[s for s in KEY_SECTIONS if s != "cover" and s not in present],
    )
    return build_xray(
        ipo_id, company, {doc.doc_type: inputs}, built_at or datetime.now(UTC), fields
    )
