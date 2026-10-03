"""The ``risks_split`` stage (B02 §3.1 step 9): Risk Factors pages → ``risks.json`` (raw risks).

The upload worker runs it after ``sections``. Residential addresses of individuals in a risk's
title or body are replaced with ``[withheld for privacy]`` (B02 §11, the same rule as the
search index). It reads the parsed document, the sections and the
tables that earlier stages handed over in ``ctx.scratch``; it joins ``upload_stages`` when the
parse and sections stages do (B1.3a).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import TypeAdapter

from finsight.core.schemas import BBox, ParsedDoc, Risk, Section, Table
from finsight.jobs import JobContext
from finsight.retrieve import redact_prose
from finsight.risks import segment_pages, to_risks
from finsight.storage import put_json

RISKS_FILE = "risks.json"
_RISKS = TypeAdapter(list[Risk])


def table_boxes(tables: Sequence[Table]) -> dict[int, list[BBox]]:
    """One box per table and page: the union of its cells' boxes."""
    boxes: dict[int, list[BBox]] = {}
    for table in tables:
        for page in sorted({c.page for c in table.cells}):
            cells = [c.bbox for c in table.cells if c.page == page]
            boxes.setdefault(page, []).append(
                (
                    min(b[0] for b in cells),
                    min(b[1] for b in cells),
                    max(b[2] for b in cells),
                    max(b[3] for b in cells),
                )
            )
    return boxes


def split_risks(
    parsed: ParsedDoc, sections: Sequence[Section], tables: Sequence[Table] = ()
) -> list[Risk]:
    """The document's risks in order; empty when no Risk Factors section was found."""
    section = next((s for s in sections if s.id == "risk_factors"), None)
    if section is None:
        return []
    pages = [p for p in parsed.pages if section.start_page <= p.number <= section.end_page]
    risks = to_risks(segment_pages(pages, table_boxes(tables), parsed.pages))
    return [
        r.model_copy(
            update={"title": redact_prose(r.title, [])[0], "body": redact_prose(r.body, [])[0]}
        )
        for r in risks
    ]


def risks_split(ctx: JobContext) -> dict[str, Any]:
    """Stage function for ``jobs.Stage("risks_split", risks_split, output="risks.json")``."""
    risks = split_risks(
        ctx.scratch["parsed"], ctx.scratch["sections"], ctx.scratch.get("tables", [])
    )
    put_json(ctx.storage, ctx.key(RISKS_FILE), _RISKS.dump_python(risks, mode="json"))
    return {"n_risks": len(risks)}
