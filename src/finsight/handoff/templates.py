"""The two frozen student prompt templates, rendered from the app's own builders.

M1 has two prompts: chat answers (``generate.prompts.build_prompt``, English and Hindi) and the
plain-English risk rewrite (``risks.simplify.student_prompt``, ``student-v1``). Both are rendered
with placeholder tokens so the files are exactly what the app sends, with the variable parts
marked. A test renders the template with real values and compares it with the builder's output.
"""

from __future__ import annotations

from finsight.core.schemas import Passage
from finsight.generate import build_prompt
from finsight.risks.simplify import PROMPT_VERSION, student_prompt

Q = "{{QUESTION}}"
PASSAGES = "{{PASSAGE_BLOCKS}}"
TITLE = "{{TITLE}}"
BODY = "{{BODY}}"

_PROBE_Q = "QQQQ-question"
_PROBE_P = "PPPP-passage"


def chat_template(language: str = "en") -> str:
    """The chat prompt with ``{{QUESTION}}`` (twice) and ``{{PASSAGE_BLOCKS}}`` as placeholders.

    A passage block renders as ``[n] (<DOC> page <p>[-<p2>])\\n<text>``; blocks are joined by a
    blank line (see ``generate.prompts._block``).
    """
    passage = Passage(
        id="x:p1:c0",
        ipo_id="x",
        doc_type="rhp",
        section_id="s",
        page_start=1,
        page_end=1,
        text=_PROBE_P,
        char_to_bbox=[],
    )
    text = build_prompt(_PROBE_Q, [passage], language).text  # type: ignore[arg-type]
    block = f"[1] (RHP page 1)\n{_PROBE_P}"
    if block not in text:
        raise ValueError("chat prompt layout changed: update finsight.handoff.templates")
    return text.replace(block, PASSAGES).replace(_PROBE_Q, Q)


def rewrite_template() -> str:
    """The risk-rewrite prompt (``student-v1``) with ``{{TITLE}}`` and ``{{BODY}}`` placeholders.

    With a title the risk text is ``Title: {{TITLE}}\\n\\n{{BODY}}``; without one it is the body.
    """
    return (
        student_prompt("TTTT-title", "BBBB-body")
        .replace("TTTT-title", TITLE)
        .replace("BBBB-body", BODY)
    )


def versions() -> dict[str, str]:
    """Prompt version labels recorded in the pack README."""
    return {"rewrite": PROMPT_VERSION, "chat": "generate.prompts.build_prompt (rules en/hi)"}
