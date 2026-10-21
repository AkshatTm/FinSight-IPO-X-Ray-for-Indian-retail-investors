"""Severe overrides (C3.2): facts are caught, negated and hedged sentences are not."""

from __future__ import annotations

import pytest

from finsight.core.schemas import ParsedDoc, Section
from finsight.redflags import detect_severe
from finsight.redflags.severe import classify, with_auditor
from finsight.risklevel import compute


def _doc(*pages: str) -> ParsedDoc:
    from finsight.core.schemas import Page

    return ParsedDoc(
        ipo_id="x",
        doc_type="rhp",
        source_path="x.pdf",
        n_pages=len(pages),
        sha256="0",
        pages=[
            Page(number=i + 1, width=1, height=1, words=[], text=t, is_scanned=False)
            for i, t in enumerate(pages)
        ],
    )


@pytest.mark.parametrize(
    ("sentence", "kind"),
    [
        (
            "The Statutory Auditors have drawn attention to a material uncertainty related to "
            "going concern in the financial statements.",
            "going_concern",
        ),
        ("Our Subsidiary has defaulted on the repayment of its term loan.", "default_or_recall"),
        ("The lender recalled the facility in March 2023.", "default_or_recall"),
        ("SEBI passed an interim order against our Promoter.", "regulator_order"),
        ("One of our Directors is a wilful defaulter.", "regulator_order"),
        ("The account was classified as fraud by a bank.", "fraud"),
        ("The auditors issued a qualified opinion on the financial statements.", "qualified_audit"),
    ],
)
def test_stated_facts_are_caught(sentence: str, kind: str) -> None:
    assert kind in classify(sentence)


@pytest.mark.parametrize(
    "sentence",
    [
        "None of our Promoters or Directors has been debarred from accessing the capital market.",
        "Our Promoters are not wilful defaulters.",
        "We may default on our borrowings, and lenders could recall the facilities.",
        "There is no material uncertainty related to going concern.",
        "The auditors issued an unqualified opinion on the financial statements.",
        "If SEBI passes an order against us, our business may be affected.",
        "Neither our Company nor our Directors have been classified as fraud.",
    ],
)
def test_negated_and_hedged_sentences_are_not(sentence: str) -> None:
    assert classify(sentence) == []


def test_detect_returns_the_first_hit_per_kind_with_its_page_and_sentence() -> None:
    doc = _doc(
        "Cover page text. Nothing to see.",
        "Risk. The Statutory Auditors have drawn attention to a material uncertainty related to "
        "going concern. Other text follows.",
        "More. The Company has defaulted on a working capital loan. Also, our Subsidiary has "
        "defaulted on a term loan.",
    )
    sections = [Section(id="summary", title="Summary", start_page=1, end_page=3, method="toc",
                        confidence=1.0)]  # fmt: skip
    found = {o.id: o for o in detect_severe(doc, sections, "doc-1")}
    assert set(found) == {"going_concern", "default_or_recall"}
    assert found["going_concern"].evidence.page == 2
    assert found["going_concern"].evidence.doc_id == "doc-1"
    assert "going concern" in (found["going_concern"].evidence.sentence or "")
    assert found["default_or_recall"].evidence.page == 3
    assert found["default_or_recall"].mentions == 2


def test_boilerplate_sections_and_pages_before_the_summary_are_not_scanned() -> None:
    doc = _doc(
        "Definitions. Wilful Defaulter has been classified as fraud by the RBI.",
        "Summary page, fine.",
        "General. The Promoter was declared a wilful defaulter.",
    )
    sections = [
        Section(id="definitions", title="D", start_page=1, end_page=1, method="toc",
                confidence=1.0),
        Section(id="summary", title="S", start_page=2, end_page=2, method="toc", confidence=1.0),
        Section(id="general_information", title="Gen", start_page=3, end_page=3, method="toc",
                confidence=1.0),
    ]  # fmt: skip
    assert detect_severe(doc, sections) == []


def test_a_qualified_summary_remark_counts_even_without_a_matching_sentence() -> None:
    from finsight.core.schemas import PageEvidence

    ev = PageEvidence(doc_id="d", page=30, sentence="Qualification: …")
    out = with_auditor(True, [], ev)
    assert [o.id for o in out] == ["qualified_audit"]
    assert out[0].evidence.page == 30
    assert with_auditor(False, [], ev) == []
    assert with_auditor(True, out, ev) == out  # not added twice


def test_any_override_forces_the_high_level_and_is_listed_first() -> None:
    doc = _doc("The Company has defaulted on a term loan.")
    sections = [Section(id="summary", title="S", start_page=1, end_page=1, method="toc",
                        confidence=1.0)]  # fmt: skip
    overrides = detect_severe(doc, sections, "d")
    plain = compute([], [])
    forced = compute([], [], overrides=overrides)
    assert plain.level != "high"
    assert forced.level == "high"
    assert forced.forced_by == ["default_or_recall"]
    assert forced.reasons[0].source == "override"
    assert forced.reasons[0].link == "#severe-default_or_recall"
    assert forced.score == plain.score  # points are not changed, only the level


def test_matches_report_fired_and_blocked_sentences() -> None:
    from finsight.redflags.severe import matches

    doc = _doc(
        "Intro sentence one. Our Subsidiary has defaulted on the repayment of its term loan. "
        "Closing sentence. The Company has not defaulted on any loan. Later text here."
    )
    rows = matches(doc, [])
    by_decision = {r.decision: r for r in rows}
    assert by_decision["fired"].kind == "default_or_recall"
    assert by_decision["fired"].before == ("Intro sentence one.",)
    assert by_decision["fired"].after[0] == "Closing sentence."
    assert by_decision["blocked_soft"].sentence.startswith("The Company has not defaulted")
    # the fired rows are exactly what the rule engine accepts
    assert [r.sentence for r in rows if r.decision == "fired"] == [
        s for s in (r.sentence for r in rows) if classify(s)
    ]
