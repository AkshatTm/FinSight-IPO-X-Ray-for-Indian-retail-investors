"""The one path from a question to a vetted answer (ADR-048).

Everything that makes a model say something to a reader goes through ``respond``: the ``ask``
CLI, the bake-off, the chat orchestrator and so, through it, the API. Three checks are therefore
impossible to bypass by taking a different route (the first Hindi bake-off did exactly that and
printed a CEO's home address):

1. **Question guard** (advice, forecasts, ratings, privacy) before any retrieval or model call.
2. **Output rules** after generation: loops, empty or pasted answers, converted units, investor
   opinions (``postprocess``), then the **privacy output filter** (addresses, phone numbers,
   e-mails and ID numbers of people).
3. The raw text stays on the ``Response``; a rejected answer is never silently turned into
   "not found" for the *record*: ``reason`` says why ("empty", "dump", "unit_converted", ...).

``on_piece`` sees tokens as they stream. They are not vetted yet: show them as a draft and replace
them with ``Response.text`` when the call returns (the chat events do this in P3.6).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from finsight.core.schemas import Passage
from finsight.generate.llm_backend import LLMUnavailable, OllamaBackend, ReasoningLeak
from finsight.generate.postprocess import LoopDetector, clean_answer
from finsight.generate.prompts import NOT_FOUND, Language, Prompt, build_prompt
from finsight.guard import check_output, check_question, refusal_text

Status = Literal["answered", "refused", "rejected", "error"]


@dataclass
class Response:
    status: Status
    text: str  # what the reader sees: the answer, a refusal, or the "not found" sentence
    reason: str | None = None  # why it is not "answered": a guard reason or a rejection code
    stage: str | None = None  # "question", "output" or "generation"
    raw: str = ""  # the model's text as it came, before any rule
    prompt: Prompt | None = None
    passages: list[Passage] = field(default_factory=list)
    trimmed: bool = False
    digits_converted: bool = False
    first_token_s: float | None = None
    total_s: float = 0.0
    error: str | None = None


def respond(
    question: str,
    language: Language,
    retrieve: Callable[[], list[Passage]],
    llm: OllamaBackend,
    *,
    budget_chars: int,
    max_tokens: int = 300,
    temperature: float = 0.2,
    on_piece: Callable[[str], None] | None = None,
) -> Response:
    started = time.perf_counter()
    guard = check_question(question)
    if guard.blocked:
        reason = guard.reason or "advice_intent"
        return Response("refused", refusal_text(reason, language), reason, "question")
    passages = retrieve()
    if not passages:
        return Response("rejected", NOT_FOUND[language], "no_passages", "retrieval")
    prompt = build_prompt(question, passages, language, budget_chars=budget_chars)
    pieces: list[str] = []
    first: float | None = None
    loop = LoopDetector()
    error: str | None = None
    try:
        for piece in llm.stream(
            prompt.text, max_tokens=max_tokens, temperature=temperature, language=language
        ):
            first = first or time.perf_counter()
            pieces.append(piece)
            if on_piece:
                on_piece(piece)
            if loop.feed(piece):
                break
    except ReasoningLeak as exc:
        error = f"reasoning_leak: {exc}"
    except LLMUnavailable as exc:
        error = f"unavailable: {exc}"
    ended = time.perf_counter()
    raw = "".join(pieces)
    timing = {
        "first_token_s": round((first or ended) - started, 2),
        "total_s": round(ended - started, 2),
    }
    common = {"raw": raw, "prompt": prompt, "passages": prompt.passages, **timing}
    if error:
        return Response("error", NOT_FOUND[language], error.split(":")[0], "generation",
                        error=error, **common)  # fmt: skip
    cleaned = clean_answer(raw, prompt.passages, language)
    if cleaned.reason:
        return Response("rejected", cleaned.text, cleaned.reason, "output",
                        trimmed=cleaned.trimmed, digits_converted=cleaned.digits_converted,
                        **common)  # fmt: skip
    leak = check_output(cleaned.text, question)
    if leak.blocked:
        return Response("refused", refusal_text("privacy", language), "privacy", "output",
                        error=f"output filter: {leak.category}", **common)  # fmt: skip
    return Response("answered", cleaned.text, None, None, trimmed=cleaned.trimmed,
                    digits_converted=cleaned.digits_converted, **common)  # fmt: skip
