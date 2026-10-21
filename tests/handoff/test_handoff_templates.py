"""The exported prompt templates are exactly what the app sends."""

from __future__ import annotations

from finsight.core.schemas import Passage
from finsight.generate import build_prompt
from finsight.handoff import chat_template, rewrite_template
from finsight.risks.simplify import student_prompt


def _passage(text: str, page: int) -> Passage:
    return Passage(
        id="i:p1:c0",
        ipo_id="i",
        doc_type="rhp",
        section_id="s",
        page_start=page,
        page_end=page,
        text=text,
        char_to_bbox=[],
    )


def test_rewrite_template_renders_to_the_builder_output() -> None:
    t = rewrite_template()
    assert t.count("{{TITLE}}") == 1
    assert t.count("{{BODY}}") == 1
    rendered = t.replace("{{TITLE}}", "Debt risk").replace("{{BODY}}", "We owe ₹5 crore.")
    assert rendered == student_prompt("Debt risk", "We owe ₹5 crore.")


def test_chat_templates_render_to_the_builder_output() -> None:
    for lang in ("en", "hi"):
        t = chat_template(lang)
        assert t.count("{{QUESTION}}") == 2
        assert t.count("{{PASSAGE_BLOCKS}}") == 1
        built = build_prompt(
            "What is the issue size?",
            [_passage("Issue size is ₹100 crore.", 1)],
            lang,  # type: ignore[arg-type]
        ).text
        block = "[1] (RHP page 1)\nIssue size is ₹100 crore."
        rendered = t.replace("{{QUESTION}}", "What is the issue size?").replace(
            "{{PASSAGE_BLOCKS}}", block
        )
        assert rendered == built
