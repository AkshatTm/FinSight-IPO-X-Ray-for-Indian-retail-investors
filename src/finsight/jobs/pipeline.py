"""The upload pipeline's stages (B02 §3.1): ``validated``, ``detected``, ``parsed``, ``sections``,
``financials``, ``redflags`` and ``risks_split`` so far; later parts append risk
scoring, risk level, simplify and index to ``upload_stages``.

Stages hand their results to later ones through ``ctx.scratch``; on a retry a cached stage is
skipped, so later stages read its stored output instead (``_parsed_doc``, ``_sections``).
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from finsight.compare import build as compare_build
from finsight.compare import compare_metrics
from finsight.compare import load_config as load_compare_config
from finsight.core.schemas import SUMMARY_HAS_VALUE, FinancialSummary, ParsedDoc, Section, XRay
from finsight.extract import upload_xray
from finsight.ingest import validate_pdf
from finsight.jobs.runner import JobContext, Stage, StageRejected
from finsight.parse import extract_tables, find_sections, parse_pdf, pymupdf_backend
from finsight.pipeline import RISKS, RISKS_FILE, split_risks
from finsight.redflags import REDFLAGS_FILE
from finsight.redflags import build as build_redflags
from finsight.storage import put_json
from finsight.summary import PEER_SECTIONS, SUMMARY_FILE, extract_summary

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


def _financials(ctx: JobContext) -> dict[str, Any]:
    parsed, sections = _parsed_doc(ctx), _sections(ctx)
    # Ruled peer tables, when PyMuPDF finds them; the summary reads the words otherwise.
    tables = _with_pdf(
        ctx,
        lambda path: extract_tables(
            path, parsed, sections, backend=pymupdf_backend, section_ids=PEER_SECTIONS
        ),
    )
    summary = extract_summary(parsed, sections, ctx.doc_id, tables=tables)
    put_json(ctx.storage, ctx.key(SUMMARY_FILE), summary.model_dump(mode="json"))
    values = [
        *summary.revenue, *summary.profit_after_tax, *summary.operating_cash_flow,
        summary.total_borrowings, summary.net_worth,
    ]  # fmt: skip
    found = sum(v is not None and v.status in SUMMARY_HAS_VALUE for v in values)
    fields = [
        summary.litigation.get("criminal_cases"), summary.litigation.get("amount_total"),
        summary.rpt_total, summary.promoter_holding_post, summary.pledged_pct,
        summary.customer_top1_pct, summary.customer_top10_pct, summary.general_purposes_pct,
        next((v for v in summary.waca if v.key == "waca_promoters"), None),
    ]  # fmt: skip
    return {
        "ready": True,
        "found": found,
        "total": len(values),
        "other_found": sum(v is not None and v.status in SUMMARY_HAS_VALUE for v in fields),
        "other_placeholder": sum(v is not None and v.status == "placeholder" for v in fields),
        "peers": len(summary.peers),
        "financial_company": summary.is_financial_company,
    }


XRAY = "xray.json"
COMPARE = "compare.json"


def _facts(ctx: JobContext) -> dict[str, Any]:
    """The fact sheet of the upload (rules + Objects table): offer price, issue split, size."""
    parsed, sections = _parsed_doc(ctx), _sections(ctx)
    tables = _with_pdf(
        ctx,
        lambda path: extract_tables(
            path, parsed, sections, backend=pymupdf_backend, section_ids=("objects_of_the_offer",)
        ),
    )
    doc = ctx.db.get_doc(ctx.doc_id)
    company = (doc.company if doc else None) or ctx.doc_id
    xray = upload_xray(parsed, sections, tables, ctx.doc_id, company)
    put_json(ctx.storage, ctx.key(XRAY), xray.model_dump(mode="json"))
    return {
        "ready": True,
        "fields": len(xray.fields),
        "with_value": sum(f.chosen is not None for f in xray.fields),
    }


def _compare(ctx: JobContext) -> dict[str, Any]:
    """Peers and where the issue sits among past IPOs (``configs/compare.yaml``)."""
    summary = FinancialSummary.model_validate_json(ctx.storage.get_bytes(ctx.key(SUMMARY_FILE)))
    if ctx.storage.exists(ctx.key(XRAY)):
        xray = XRay.model_validate_json(ctx.storage.get_bytes(ctx.key(XRAY)))
    else:  # the facts stage failed: peers and the P/E still compare, the rest is left out
        xray = XRay(
            ipo_id=ctx.doc_id, company="", built_at=datetime.now(UTC), fields=[], derived={}
        )
    metrics, price = compare_metrics(xray, summary)
    result = compare_build(
        ctx.storage, ctx.doc_id, summary.peers, metrics, price, load_compare_config()
    )
    return {
        "ready": True,
        "peers": len(result.peers),
        "percentiles": [p.metric for p in result.percentiles],
        "provisional": result.provisional,
    }


def _redflags(ctx: JobContext) -> dict[str, Any]:
    flags = build_redflags(ctx.storage, ctx.doc_id, _parsed_doc(ctx), _sections(ctx))
    by_status: dict[str, int] = {}
    for f in flags.flags:
        by_status[f.status] = by_status.get(f.status, 0) + 1
    return {
        "ready": True,
        "n_flags": len(flags.flags),
        "concern": by_status.get("concern", 0),
        "watch": by_status.get("watch", 0),
        "severe": [o.id for o in flags.severe_overrides],
    }


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


def upload_stages(models: bool = True) -> list[Stage]:
    """Stages for an uploaded document, in order (B02 §3.1); ``models`` adds the stages that
    use the trained models and publish the workspace (C3.3)."""
    from finsight.jobs.model_stages import model_stages

    return [
        Stage("validated", _validated, critical=True),
        Stage("detected", _detected, output=None, requires=("validated",), critical=True),
        Stage("parsed", _parsed, output=PARSED, requires=("detected",), critical=True),
        Stage("sections", _sections_stage, output=SECTIONS, requires=("parsed",)),
        Stage("facts", _facts, output=XRAY, requires=("sections",)),
        Stage("financials", _financials, output=SUMMARY_FILE, requires=("sections",)),
        Stage("redflags", _redflags, output=REDFLAGS_FILE, requires=("financials",)),
        Stage("compare", _compare, output=COMPARE, requires=("financials",)),
        Stage("risks_split", _risks_split, output=RISKS_FILE, requires=("sections",)),
        *(model_stages() if models else []),
    ]
