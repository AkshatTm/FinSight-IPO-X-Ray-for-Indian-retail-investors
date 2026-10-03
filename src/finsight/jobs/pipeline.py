"""The upload pipeline's stages (B02 §3.1): ``validated``, ``detected``, ``parsed``, ``sections``
and ``risks_split`` so far; later parts append facts, financials, red flags, risk scoring, risk
level, simplify, index and compare to ``upload_stages``.

Stages hand their results to later ones through ``ctx.scratch``; on a retry a cached stage is
skipped, so later stages read its stored output instead (``_parsed_doc``, ``_sections``).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from finsight.core.schemas import ParsedDoc, Section
from finsight.ingest import validate_pdf
from finsight.jobs.runner import JobContext, Stage, StageRejected
from finsight.parse import extract_tables, find_sections, parse_pdf, pymupdf_backend
from finsight.pipeline import RISKS, RISKS_FILE, split_risks
from finsight.storage import put_json

SOURCE = "source.pdf"
PARSED = "parsed.json"
SECTIONS = "sections.json"
_SECTIONS = TypeAdapter(list[Section])


def _validated(ctx: JobContext) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / SOURCE
        path.write_bytes(ctx.storage.get_bytes(ctx.key(SOURCE)))
        check = validate_pdf(path, ctx.settings.uploads)
    if not check.ok:
        assert check.code is not None
        raise StageRejected(check.code, check.detail)
    ctx.scratch["check"] = check
    return {"ok": True}


def _detected(ctx: JobContext) -> dict[str, Any]:
    check = ctx.scratch["check"]
    doc = ctx.db.get_doc(ctx.doc_id)
    company = doc.company if doc else None
    ctx.db.update_doc(ctx.doc_id, doc_type=check.doc_type, pages=check.pages)
    payload = {"doc_type": check.doc_type, "company": company, "pages": check.pages}
    put_json(ctx.storage, ctx.key("doc.json"), payload)
    return payload


def _with_pdf(ctx: JobContext, fn: Any) -> Any:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / SOURCE
        path.write_bytes(ctx.storage.get_bytes(ctx.key(SOURCE)))
        return fn(path)


def _parsed(ctx: JobContext) -> dict[str, Any]:
    doc_type = ctx.scratch["check"].doc_type
    parsed: ParsedDoc = _with_pdf(ctx, lambda path: parse_pdf(path, ctx.doc_id, doc_type))
    ctx.storage.put_bytes(ctx.key(PARSED), parsed.model_dump_json().encode(), "application/json")
    ctx.scratch["parsed"] = parsed
    return {"pages_done": parsed.n_pages, "pages_total": parsed.n_pages}


def _parsed_doc(ctx: JobContext) -> ParsedDoc:
    if "parsed" not in ctx.scratch:
        ctx.scratch["parsed"] = ParsedDoc.model_validate_json(
            ctx.storage.get_bytes(ctx.key(PARSED))
        )
    parsed: ParsedDoc = ctx.scratch["parsed"]
    return parsed


def _sections_stage(ctx: JobContext) -> dict[str, Any]:
    sections = find_sections(_parsed_doc(ctx))
    put_json(ctx.storage, ctx.key(SECTIONS), _SECTIONS.dump_python(sections, mode="json"))
    ctx.scratch["sections"] = sections
    return {"found": [s.id for s in sections]}


def _sections(ctx: JobContext) -> list[Section]:
    if "sections" not in ctx.scratch:
        ctx.scratch["sections"] = _SECTIONS.validate_json(ctx.storage.get_bytes(ctx.key(SECTIONS)))
    sections: list[Section] = ctx.scratch["sections"]
    return sections


def _risks_split(ctx: JobContext) -> dict[str, Any]:
    parsed, sections = _parsed_doc(ctx), _sections(ctx)
    # Bold table headers must not start a risk, so the Risk Factors tables are found first.
    tables = _with_pdf(
        ctx,
        lambda path: extract_tables(
            path, parsed, sections, backend=pymupdf_backend, section_ids=("risk_factors",)
        ),
    )
    risks = split_risks(parsed, sections, tables)
    put_json(ctx.storage, ctx.key(RISKS_FILE), RISKS.dump_python(risks, mode="json"))
    return {"n_risks": len(risks)}


def upload_stages() -> list[Stage]:
    """Stages for an uploaded document, in order (B02 §3.1)."""
    return [
        Stage("validated", _validated, critical=True),
        Stage("detected", _detected, output=None, requires=("validated",), critical=True),
        Stage("parsed", _parsed, output=PARSED, requires=("detected",), critical=True),
        Stage("sections", _sections_stage, output=SECTIONS, requires=("parsed",)),
        Stage("risks_split", _risks_split, output=RISKS_FILE, requires=("sections",)),
    ]
