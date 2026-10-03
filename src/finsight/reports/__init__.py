"""Assemble ``report.json`` (the overview of B06 §3) from whatever stage outputs exist.

A part whose stage has not run, or failed, is ``null``; the UI shows its "not available" state.
Later parts fill the inputs: summary (B1.3a), red flags (B1.4), risks (B2.1a–B2.5a),
risk level (B2.6a), compare (B3.2).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from finsight.core.schemas import DocRecord
from finsight.storage import Storage, doc_key, get_json, put_json

TOP_RISKS = 5


class ReportOverview(BaseModel):
    """``GET /api/docs/{doc_id}/report``."""

    doc: DocRecord
    companion_doc_id: str | None = None
    facts_summary: dict[str, Any] | None = None
    risk_level: dict[str, Any] | None = None
    top_risks: list[dict[str, Any]] | None = None
    redflags_summary: list[dict[str, Any]] | None = None
    offer_line_params: dict[str, Any] | None = None


def _read(storage: Storage, doc_id: str, name: str) -> Any:
    key = doc_key(doc_id, name)
    return get_json(storage, key) if storage.exists(key) else None


def assemble(
    storage: Storage, doc: DocRecord, companion_doc_id: str | None = None
) -> ReportOverview:
    """Build the overview from the stage outputs in ``docs/<doc_id>/``."""
    summary = _read(storage, doc.doc_id, "summary.json")
    redflags = _read(storage, doc.doc_id, "redflags.json")
    risks = _read(storage, doc.doc_id, "risks.json")
    top = None
    # risks.json is a list of Risk (B2.2a); the early {"risks": [...]} shape is still read.
    rows = risks.get("risks") if isinstance(risks, dict) else risks
    if isinstance(rows, list):
        ranked = sorted(
            rows, key=lambda r: (-float(r.get("importance") or 0.0), int(r.get("order") or 0))
        )
        top = ranked[:TOP_RISKS]
    flags = None
    if isinstance(redflags, dict) and isinstance(redflags.get("flags"), list):
        flags = [{"id": f.get("id"), "status": f.get("status")} for f in redflags["flags"]]
    return ReportOverview(
        doc=doc,
        companion_doc_id=companion_doc_id,
        facts_summary=summary if isinstance(summary, dict) else None,
        risk_level=_read(storage, doc.doc_id, "risklevel.json"),
        top_risks=top,
        redflags_summary=flags,
        offer_line_params=(summary or {}).get("offer_line_params")
        if isinstance(summary, dict)
        else None,
    )


def write_report(
    storage: Storage, doc: DocRecord, companion_doc_id: str | None = None
) -> ReportOverview:
    report = assemble(storage, doc, companion_doc_id)
    put_json(storage, doc_key(doc.doc_id, "report.json"), report.model_dump(mode="json"))
    return report


def etag(report: ReportOverview) -> str:
    """A strong ETag over the report's JSON (B06 §3)."""
    body = json.dumps(report.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    return '"' + hashlib.sha256(body).hexdigest()[:32] + '"'


__all__ = ["TOP_RISKS", "ReportOverview", "assemble", "etag", "write_report"]
