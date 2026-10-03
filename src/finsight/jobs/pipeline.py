"""The upload pipeline's stages (B02 §3.1). B1.2 ships ``validated`` and ``detected``; later parts
append their stages (sections, facts, financials, red flags, risks, risk level, simplify, index,
compare) to ``upload_stages``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from finsight.ingest import validate_pdf
from finsight.jobs.runner import JobContext, Stage, StageRejected
from finsight.storage import put_json

SOURCE = "source.pdf"


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


def upload_stages() -> list[Stage]:
    """Stages for an uploaded document, in order."""
    return [
        Stage("validated", _validated, critical=True),
        Stage("detected", _detected, output=None, requires=("validated",), critical=True),
    ]
