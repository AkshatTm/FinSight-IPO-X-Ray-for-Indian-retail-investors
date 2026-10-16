"""C3.3: red-flag questions about an upload are answered from the report's checks."""

from __future__ import annotations

from finsight.chat.redflags import redflags_passage, wants_redflags
from finsight.core.schemas import PageEvidence, RedFlag, RedFlags, SevereOverride


def _flag(i: str, status: str, sentence: str, page: int | None = None) -> RedFlag:
    ev = [PageEvidence(doc_id="doc_x", page=page)] if page else []
    return RedFlag(id=i, title=f"Check {i}", status=status, sentence=sentence, evidence=ev)  # type: ignore[arg-type]


def test_questions_that_ask_for_the_checks() -> None:
    assert wants_redflags("Are there any red flags?")
    assert wants_redflags("what did the promoters paid for their shares")
    assert wants_redflags("क्या कोई रेड फ्लैग है?")
    assert not wants_redflags("How much is the fresh issue?")


def test_the_passage_lists_run_checks_and_points_at_the_first_concern_page() -> None:
    flags = RedFlags(
        flags=[
            _flag("RF01", "ok", "Profit last year was ₹12 million."),
            _flag("RF03", "concern", "Debt is 3.2× its net worth.", page=211),
            _flag("RF04", "not_available", "Not available."),
        ]
    )
    p = redflags_passage("doc_x", flags)
    assert p is not None
    assert p.page_start == 211
    assert "Debt is 3.2× its net worth." in p.text
    assert "Not available." not in p.text
    assert "1 more checks could not be run" in p.text


def test_no_runnable_check_gives_no_passage() -> None:
    none = RedFlags(flags=[_flag("RF01", "not_available", "n/a")])
    assert redflags_passage("doc_x", none) is None
    sev = SevereOverride(
        id="going_concern",
        title="Going concern",
        sentence="Doubt about going concern.",
        evidence=PageEvidence(doc_id="doc_x", page=9),
        mentions=1,
    )
    assert redflags_passage("doc_x", RedFlags(severe_overrides=[sev])) is not None
