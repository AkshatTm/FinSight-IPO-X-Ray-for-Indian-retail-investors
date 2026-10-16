"""Red-flag questions are answered from the checks FinSight already ran on the document.

"Are there any red flags about debt?" is not a question the text of an offer document answers:
the 13 checks compare numbers from several pages. For an uploaded document the chat leads with
one passage that lists each check with its status and the sentence the report shows, so the
answer matches the Red flags tab. It describes what the document discloses; it never says
whether to apply (the no-advice note is added as for every red-flag question, C3.7).
"""

from __future__ import annotations

import re

from finsight.core.schemas import Passage, RedFlags
from finsight.guard import is_red_flag_question

_ASKS = re.compile(
    r"red[\s-]?flags?|warning signs?|\bconcerns?\b|how risky|is it risky|"
    r"promoters? (?:paid|bought)|what insiders paid|(?:too much|high) debt|\bdebt\b.*\bflag",
    re.IGNORECASE,
)
_LABEL = {"concern": "Concern", "watch": "Watch", "ok": "OK"}
_SKIPPED = ("not_available", "not_applicable")


def wants_redflags(question: str) -> bool:
    """Whether the question is about the document's red flags."""
    return is_red_flag_question(question) or bool(_ASKS.search(question))


def redflags_passage(ipo_id: str, flags: RedFlags) -> Passage | None:
    """One passage listing the checks that could be run, or ``None`` when none could."""
    lines = []
    page = 1
    for f in flags.flags:
        if f.status in _SKIPPED:
            continue
        lines.append(f"- {f.title} [{_LABEL.get(f.status, f.status)}]: {f.sentence}")
        if f.status != "ok" and f.evidence and page == 1:
            page = f.evidence[0].page
    for o in flags.severe_overrides:
        lines.append(f"- Severe: {o.title}: {o.sentence}")
        if o.evidence:
            page = o.evidence.page
    if not lines:
        return None
    skipped = sum(f.status in _SKIPPED for f in flags.flags)
    head = "FinSight's red-flag checks on this document, computed from its own numbers:"
    tail = f"{skipped} more checks could not be run on this document." if skipped else ""
    return Passage(
        id=f"{ipo_id}:redflags",
        ipo_id=ipo_id,
        doc_type="rhp",
        section_id="red_flags",
        page_start=page,
        page_end=page,
        text="\n".join([head, *lines, tail]).strip(),
        char_to_bbox=[],
    )
