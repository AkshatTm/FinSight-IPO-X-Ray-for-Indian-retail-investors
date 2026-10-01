"""Layer 1 of the privacy fix (ADR-048): one guarded path for every generation caller."""

from collections.abc import Iterator
from typing import Any

from finsight.core.schemas import Passage
from finsight.generate import respond
from finsight.generate.llm_backend import LLMUnavailable, ReasoningLeak


def passage(text: str = "The Registrar to the Offer is KFin Technologies Limited.") -> Passage:
    return Passage(
        id="i:p3:c0", ipo_id="i", doc_type="rhp", section_id="s", page_start=3, page_end=3,
        text=text, char_to_bbox=[],
    )  # fmt: skip


class FakeLLM:
    def __init__(self, *pieces: str, error: Exception | None = None) -> None:
        self.pieces, self.error, self.calls = pieces, error, 0

    def stream(self, prompt: str, **_: Any) -> Iterator[str]:
        self.calls += 1
        yield from self.pieces
        if self.error:
            raise self.error


def run(question: str, llm: FakeLLM, passages: list[Passage] | None = None, lang: str = "en"):
    retrieved: list[int] = []

    def retrieve() -> list[Passage]:
        retrieved.append(1)
        return passages if passages is not None else [passage()]

    result = respond(question, lang, retrieve, llm, budget_chars=3000)  # type: ignore[arg-type]
    return result, retrieved


def test_privacy_question_is_refused_before_retrieval_and_model() -> None:
    llm = FakeLLM("never used")
    result, retrieved = run("What is the home address of the company's CEO?", llm)
    assert result.status == "refused"
    assert result.reason == "privacy"
    assert result.stage == "question"
    assert llm.calls == 0
    assert not retrieved


def test_hindi_privacy_and_advice_questions_are_refused() -> None:
    for question, reason in (
        ("कंपनी के सीईओ का घर का पता क्या है?", "privacy"),
        ("क्या मुझे इस IPO में निवेश करना चाहिए?", "advice_intent"),
    ):
        llm = FakeLLM("x")
        result, _ = run(question, llm, lang="hi")
        assert (result.status, result.reason, llm.calls) == ("refused", reason, 0)


def test_a_leaked_address_in_the_answer_is_blocked_by_the_output_filter() -> None:
    llm = FakeLLM("The chief executive's home is House No. 8A, Sector 22, Gurugram [1].")
    result, _ = run("Who is the chief executive?", llm)
    assert result.status == "refused"
    assert result.stage == "output"
    assert result.reason == "privacy"
    assert "Sector 22" not in result.text
    assert "Sector 22" in result.raw  # the record keeps what the model said


def test_good_answer_is_returned_with_timings() -> None:
    result, _ = run(
        "Who is the registrar?", FakeLLM("The registrar is ", "KFin Technologies Limited [1].")
    )
    assert result.status == "answered"
    assert result.reason is None
    assert result.text == "The registrar is KFin Technologies Limited [1]."
    assert result.passages
    assert result.first_token_s is not None


def test_empty_output_is_recorded_as_empty_not_hidden() -> None:
    result, _ = run("Who is the registrar?", FakeLLM())
    assert result.status == "rejected"
    assert result.reason == "empty"
    assert result.raw == ""
    assert "could not find" in result.text


def test_citation_only_dump_and_opinion_are_rejected_with_a_reason() -> None:
    assert run("q", FakeLLM("[1][2]"))[0].reason == "citation_only"
    result, _ = run(
        "Who is the registrar?", FakeLLM("Investors should be careful with this IPO [1].")
    )
    assert result.status == "rejected"
    assert result.reason == "opinion"


def test_converted_unit_is_rejected() -> None:
    passages = [passage("The fresh issue is up to ₹ 26,260 million.")]
    result, _ = run(
        "How big is the fresh issue?", FakeLLM("The fresh issue is ₹ 2,626 crore [1]."), passages
    )
    assert result.reason == "unit_converted"
    ok, _ = run(
        "How big is the fresh issue?", FakeLLM("The fresh issue is ₹ 26,260 million [1]."), passages
    )
    assert ok.status == "answered"


def test_devanagari_digits_are_converted_and_flagged() -> None:
    passages = [passage("The offer price is ₹ 321 per equity share.")]
    result, _ = run("ऑफ़र प्राइस?", FakeLLM("ऑफ़र प्राइस ₹ ३२१ प्रति शेयर है [1]।"), passages, lang="hi")
    assert result.status == "answered"
    assert result.digits_converted
    assert "321" in result.text
    assert "३" not in result.text


def test_backend_failures_become_error_responses() -> None:
    gone, _ = run("q", FakeLLM(error=LLMUnavailable("down")))
    assert gone.status == "error"
    assert gone.reason == "unavailable"
    leak, _ = run("q", FakeLLM(error=ReasoningLeak("thinking")))
    assert leak.status == "error"
    assert leak.reason == "reasoning_leak"


def test_no_passages_is_a_not_found() -> None:
    llm = FakeLLM("x")
    result, _ = run("Who is the registrar?", llm, passages=[])
    assert result.reason == "no_passages"
    assert llm.calls == 0
