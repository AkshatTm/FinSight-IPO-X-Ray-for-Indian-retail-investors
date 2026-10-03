"""Risk Factors pages → raw risks, for the ``risks_split`` upload stage (B02 §3.1 step 9).

``jobs.upload_stages`` runs it after ``sections`` and writes ``risks.json``. Residential
addresses of individuals in a risk's title or body are replaced with ``[withheld for privacy]``
(B02 §11, the same rule as the search index).
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import TypeAdapter

from finsight.core.schemas import BBox, ParsedDoc, Risk, Section, Table
from finsight.retrieve import redact_prose
from finsight.risks import segment_pages, to_risks

RISKS_FILE = "risks.json"
RISKS = TypeAdapter(list[Risk])


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
