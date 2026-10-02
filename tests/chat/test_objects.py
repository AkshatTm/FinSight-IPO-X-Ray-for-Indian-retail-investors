from datetime import UTC, datetime

from finsight.chat import ChatOrchestrator, TraceStore
from finsight.chat.objects import amount_with_unit, objects_passage, table_passage
from finsight.core.schemas import Candidate, FieldResult, Passage, TableValue, XRay
from finsight.retrieve import Hit, SearchResult

ROWS = [
    ["Capital expenditure for the factory", "9,272 (₹ in million)"],
    ["General corporate purposes", "[●] (₹ in million)"],
]
FULL = [["Capital expenditure for the factory", "9,272 (₹ in million)"],
        ["General corporate purposes", "4,922 (₹ in million)"]]  # fmt: skip


def candidate(doc: str, rows: list[list[str]], page: int) -> Candidate:
    raw = " | ".join(f"{a} :: {b}" for a, b in rows)
    return Candidate(
        field_id="objects_of_offer", extractor="table", doc_type=doc, raw=raw,  # type: ignore[arg-type]
        value=TableValue(columns=["Purpose", "Amount"], rows=rows), page=page, score=0.9,
    )  # fmt: skip


def xray(chosen: Candidate | None, others: list[Candidate], reason: str = "ok") -> XRay:
    field = FieldResult(
        field_id="objects_of_offer", chosen=chosen, candidates=others, verdict="verified",
        reason_code="verified", reason=reason, checks=[],
    )  # fmt: skip
    return XRay(ipo_id="a", company="A", built_at=datetime.now(UTC), fields=[field], derived={})


def test_amount_keeps_the_unit_the_table_header_prints() -> None:
    assert amount_with_unit("9,272 (₹ in million)") == "₹ 9,272 million"
    assert amount_with_unit("1,000.50 (₹ in crore)") == "₹ 1,000.50 crore"
    assert amount_with_unit("[●] (₹ in million)").startswith("[●]")
    assert amount_with_unit("5,000") == "5,000"


def test_prospectus_table_with_every_amount_beats_the_rhp_placeholder_table() -> None:
    rhp, pro = candidate("rhp", ROWS, 171), candidate("prospectus", FULL, 172)
    p = objects_passage(xray(rhp, [rhp, pro]), [])
    assert p is not None
    assert (p.doc_type, p.page_start) == ("prospectus", 172)
    assert "1. Capital expenditure for the factory: ₹ 9,272 million" in p.text
    assert "2. General corporate purposes: ₹ 4,922 million" in p.text
    assert table_passage("a", rhp).text.count("not yet fixed") == 1


def test_pure_offer_for_sale_leads_with_a_short_no_proceeds_passage() -> None:
    real = Passage(
        id="a:p135:c0", ipo_id="a", doc_type="prospectus", section_id="objects_of_the_offer",
        page_start=135, page_end=135, char_to_bbox=[],
        text="OBJECTS OF THE OFFER The objects of the Offer are to carry out the Offer for Sale "
        "of up to 1,000 Equity Shares. Our Company will not receive any proceeds from the Offer "
        "and all the proceeds will go to the Selling Shareholder.",
    )  # fmt: skip
    p = objects_passage(
        xray(None, [], "Pure offer for sale: the company receives no proceeds."), [real]
    )
    assert p is not None
    assert p.page_start == 135
    assert "will not receive any money" in p.text


def test_nothing_to_lead_with_when_the_table_was_not_read() -> None:
    assert objects_passage(xray(None, [], "no table found"), []) is None


def test_use_of_money_question_leads_with_the_pinned_passage_alone() -> None:
    other = Passage(
        id="a:p9:c0", ipo_id="a", doc_type="rhp", section_id="risk", page_start=9, page_end=9,
        text="Risk text.", char_to_bbox=[],
    )  # fmt: skip
    pinned = table_passage("a", candidate("prospectus", FULL, 172))

    class LLM:
        prompt = ""

        def stream(self, prompt: str, **_: object):  # type: ignore[no-untyped-def]
            LLM.prompt = prompt
            yield "The factory costs ₹ 9,272 million [1]."

    c = ChatOrchestrator(
        search=lambda q, i: SearchResult([Hit(other, 0.4, 1)], "hybrid", True, 0.4),
        llm=LLM(),  # type: ignore[arg-type]
        traces=TraceStore(":memory:"), facts=lambda i: [], budget_chars=4000,
        pin_objects=lambda i: pinned,
    )  # fmt: skip
    events = list(c.events("a", "What will the money be used for?"))
    names = [n for n, _ in events]
    assert "abstain" not in names  # a weak retrieval score no longer hides the table
    retrieval = next(e for n, e in events if n == "retrieval")
    assert [p.id for p in retrieval.passages] == [pinned.id]
    verdict = next(e for n, e in events if n == "verdict")
    assert verdict.status == "verified"
    assert verdict.evidence is not None
    assert verdict.evidence.page == 172
    # an unrelated question is not pinned
    events = list(c.events("a", "Who is the registrar?"))
    assert "abstain" in [n for n, _ in events]
