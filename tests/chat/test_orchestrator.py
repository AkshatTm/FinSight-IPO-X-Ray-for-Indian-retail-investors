"""The event stream of one chat turn, with a fake retriever and a fake model (no Ollama)."""

from collections.abc import Iterator
from typing import Any

from finsight.chat import ChatOrchestrator, TraceStore
from finsight.core.schemas import Passage
from finsight.generate.llm_backend import LLMUnavailable
from finsight.retrieve import Hit, SearchResult

TEXT = "Fresh Issue of up to Rs. 26,260 million. Offer for Sale of up to 11,051,746 Equity Shares."


def passage(pid: str = "a:p3:c0", text: str = TEXT, page: int = 3) -> Passage:
    return Passage(
        id=pid, ipo_id="a", doc_type="rhp", section_id="the_offer", page_start=page,
        page_end=page, text=text, char_to_bbox=[(0, len(text), page, (10.0, 20.0, 300.0, 34.0))],
    )  # fmt: skip


class FakeLLM:
    def __init__(self, *pieces: str, error: Exception | None = None) -> None:
        self.pieces, self.error = pieces, error

    def stream(self, prompt: str, **_: Any) -> Iterator[str]:
        yield from self.pieces
        if self.error:
            raise self.error


def chat(llm: FakeLLM, result: SearchResult | None = None) -> ChatOrchestrator:
    hits = [Hit(passage(), 0.9, 1), Hit(passage("a:p9:c0", "Risk factors text.", 9), 0.2, 2)]
    found = result or SearchResult(hits, "hybrid+rerank", False, 0.9)
    return ChatOrchestrator(
        search=lambda q, ipo: found, llm=llm,  # type: ignore[arg-type]
        traces=TraceStore(":memory:"), facts=lambda ipo: [], budget_chars=3000,
    )  # fmt: skip


def names(events: list[tuple[str, Any]]) -> list[str]:
    return [n for n, _ in events]


def test_normal_answer_emits_the_contract_order_and_a_verified_number() -> None:
    c = chat(FakeLLM("The fresh issue is ", "Rs. 26,260 million [1]."))
    events = list(c.events("a", "How big is the fresh issue?"))
    order = names(events)
    assert order[0] == "stage"
    assert order[-1] == "final"
    assert [o for o in order if o not in ("stage", "token")] == [
        "retrieval",
        "answer",
        "verdict",
        "final",
    ]
    stages = [(e.name, e.status) for n, e in events if n == "stage"]
    assert stages == [
        ("guard", "start"), ("guard", "end"), ("retrieving", "start"), ("retrieving", "end"),
        ("generating", "start"), ("generating", "end"),
        ("verifying", "start"), ("verifying", "end"),
    ]  # fmt: skip
    verdict = next(e for n, e in events if n == "verdict")
    assert verdict.status == "verified"
    assert verdict.evidence is not None
    assert verdict.evidence.page == 3
    assert verdict.evidence.bbox == (10.0, 20.0, 300.0, 34.0)
    answer = next(e for n, e in events if n == "answer")
    assert answer.citations[0].n == 1
    final = events[-1][1]
    assert final.score == 1.0
    assert final.n_numbers == 1
    assert set(final.timings_ms) == {"guard", "retrieving", "generating", "verifying"}


def test_scale_trick_is_contradicted() -> None:
    events = list(
        chat(FakeLLM("The fresh issue is Rs. 26,260 lakh [1].")).events("a", "fresh issue?")
    )
    verdict = next(e for n, e in events if n == "verdict")
    assert verdict.status == "contradicted"
    assert verdict.reason_code == "scale_mismatch"
    assert events[-1][1].score == 0.0


def test_dropped_passages_are_reported_when_the_budget_is_small() -> None:
    c = chat(FakeLLM("Rs. 26,260 million [1]."))
    c.budget_chars = 120
    retrieval = next(e for n, e in c.events("a", "q") if n == "retrieval")
    assert len(retrieval.passages) + len(retrieval.dropped) == 2


def test_advice_question_is_refused_with_guard_and_final_only() -> None:
    llm = FakeLLM("never")
    events = list(chat(llm).events("a", "Should I apply for this IPO?"))
    assert names(events) == ["stage", "stage", "guard", "final"]
    guard = events[2][1]
    assert guard.blocked
    assert guard.reason == "advice_intent"


def test_forecast_question_gets_the_forecast_reason() -> None:
    events = list(chat(FakeLLM("never")).events("a", "Will this IPO double on listing?"))
    assert events[2][1].reason == "forecast"


def test_privacy_question_is_blocked() -> None:
    events = list(chat(FakeLLM("never")).events("a", "What is the home address of the CEO?"))
    assert events[2][1].reason == "privacy"


def test_low_retrieval_score_abstains() -> None:
    result = SearchResult([Hit(passage(), 0.05, 1)], "hybrid+rerank", True, 0.05)
    events = list(chat(FakeLLM("never"), result).events("a", "Who won the cricket match?"))
    assert [n for n, _ in events if n not in ("stage",)] == ["abstain", "final"]
    abstain = next(e for n, e in events if n == "abstain")
    assert abstain.reason == "low_retrieval_score"
    assert abstain.closest_passage.page_start == 3


def test_every_turn_writes_a_trace_with_the_prompt() -> None:
    c = chat(FakeLLM("Rs. 26,260 million [1]."))
    events = list(c.events("a", "How big is the fresh issue?"))
    trace = c.traces.get(events[-1][1].trace_id)
    assert trace is not None
    assert "How big is the fresh issue?" in trace.prompt
    assert len(trace.passages) == 2
    assert trace.checks[0].status == "verified"
    blocked = chat(FakeLLM("x"))
    ev = list(blocked.events("a", "Should I apply?"))
    assert blocked.traces.get(ev[-1][1].trace_id) is not None


def test_model_down_becomes_one_error_event() -> None:
    events = list(chat(FakeLLM(error=LLMUnavailable("ollama is down"))).events("a", "q?"))
    assert events[-1][0] == "error"
    assert events[-1][1].code == "llm_unavailable"
    assert "final" not in names(events)


def test_a_rejected_answer_is_sent_as_not_found_without_verdicts() -> None:
    events = list(chat(FakeLLM("")).events("a", "q?"))
    answer = next(e for n, e in events if n == "answer")
    assert "could not find" in answer.text
    assert "verdict" not in names(events)
