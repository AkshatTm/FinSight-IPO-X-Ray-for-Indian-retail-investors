"""One question in, the contract's SSE events out (06_API_CONTRACT.md, ``POST /api/chat``).

Order: ``stage guard`` -> (``guard`` + ``final`` when blocked) -> ``stage retrieving`` ->
(``abstain`` + ``final`` when the best passage scores too low) -> ``retrieval`` -> ``stage
generating`` -> ``token``\\* -> ``answer`` -> ``stage verifying`` -> ``verdict``\\* -> ``final``.
Every turn, including refusals and abstentions, writes a trace. Failures become one ``error``
event and the stream closes; nothing raises out of ``stream``.

Everything the model says goes through ``generate.respond`` (ADR-048), so the guard, the output
rules and the privacy filter cannot be bypassed from here. The tokens streamed are a draft; the
``answer`` event carries the vetted text and replaces them.

Retrieval is injected as a callable so tests run without indexes or models; ``from_settings``
wires the real one.
"""

from __future__ import annotations

import queue
import re
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from pydantic import BaseModel

from finsight.api.events import (
    AbstainEvent,
    AnswerEvent,
    Citation,
    ErrorEvent,
    Evidence,
    FactSummary,
    FinalEvent,
    GuardEvent,
    RetrievalEvent,
    RetrievedPassage,
    StageEvent,
    TokenEvent,
    VerdictEvent,
)
from finsight.chat.objects import objects_passage
from finsight.chat.traces import TraceStore, new_trace_id
from finsight.core.schemas import CheckResult, Language, Passage, Trace
from finsight.generate import (
    LLMUnavailable,
    OllamaBackend,
    ReasoningLeak,
    build_prompt,
    respond,
)
from finsight.guard import check_question, facts_payload
from finsight.retrieve import Hit, SearchResult, wants_objects
from finsight.verify import NumberVerdict, verify_answer

Event = tuple[str, BaseModel]
Search = Callable[[str, str], SearchResult]
FactsLoader = Callable[[str], list[FactSummary]]
Pin = Callable[[str], Passage | None]  # ipo id -> the objects-of-the-offer passage, if any

_CITATION = re.compile(r"\[(\d+)\]")
_DONE = object()


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _passage_event(
    n: int, p: Passage, rank: int | None, method: str, score: float | None
) -> RetrievedPassage:
    """Only the fused rank and the final score are known per passage (bm25/dense ranks are not
    exposed by ``Retriever.search``), so the other two stay ``None``."""
    return RetrievedPassage(
        n=n,
        id=p.id,
        doc=p.doc_type,
        page_start=p.page_start,
        page_end=p.page_end,
        section=p.section_id,
        snippet=" ".join(p.text.split())[:240],
        bm25_rank=None,
        dense_rank=None,
        fused_rank=rank,
        rerank_score=round(score, 4) if score is not None and "rerank" in method else None,
    )


def _evidence(check: CheckResult, passages: dict[str, Passage]) -> Evidence | None:
    p = passages.get(check.evidence_passage_id or "")
    if p is None or check.evidence_char_span is None:
        return None
    lo, hi = check.evidence_char_span
    box = next((b for s, e, _page, b in p.char_to_bbox if s < hi and e > lo), None)
    page = next((pg for s, e, pg, _b in p.char_to_bbox if s < hi and e > lo), p.page_start)
    return Evidence(
        passage_id=p.id, doc=p.doc_type, page=page, char_span=(lo, hi), bbox=box,
        value=check.evidence_value,
    )  # fmt: skip


def verdict_event(v: NumberVerdict, passages: dict[str, Passage]) -> VerdictEvent | None:
    c = v.check
    if c.answer_value is None:
        return None
    return VerdictEvent(
        index=v.index,
        answer_char_span=v.answer_char_span,
        answer_value=c.answer_value,
        status=c.status,
        reason_code=c.reason_code,
        reason=c.reason,
        evidence=_evidence(c, passages),
    )


@dataclass
class ChatOrchestrator:
    search: Search
    llm: OllamaBackend
    traces: TraceStore
    facts: FactsLoader
    budget_chars: int
    max_tokens: int = 300
    pin_objects: Pin | None = None

    @classmethod
    def from_settings(cls, profile: str | None = None) -> ChatOrchestrator:
        """The real wiring: retriever per the profile, Ollama LLM, SQLite traces, X-Ray facts."""
        from finsight.core.config import get_settings, load_settings
        from finsight.extract import load_fields
        from finsight.generate import get_llm
        from finsight.pipeline.xray_stage import load_xray
        from finsight.retrieve import BgeM3Embedder, CrossEncoderReranker, Retriever

        settings = load_settings(profile) if profile else get_settings()
        embedder = reranker = None
        try:
            if settings.retrieve.dense:
                embedder = BgeM3Embedder()
            if settings.retrieve.rerank:
                reranker = CrossEncoderReranker()
        except ImportError:  # the ml group is not installed: BM25 answers alone
            pass
        retriever = Retriever(
            settings.paths.processed_dir,
            embedder=embedder,
            reranker=reranker,
            pool=settings.retrieve.rerank_top_n,
            thresholds=settings.retrieve.abstain_thresholds,
            top_k=settings.retrieve.final_top_k,
        )
        fields = load_fields()

        def facts(ipo_id: str) -> list[FactSummary]:
            try:
                xray = load_xray(settings.paths.processed_dir, ipo_id)
            except FileNotFoundError:
                return []
            hi = {f["field_id"]: f for f in facts_payload(xray, fields, "hi")}
            return [
                FactSummary(
                    field_id=f["field_id"],
                    label_en=f["label"],
                    label_hi=hi.get(f["field_id"], f)["label"],
                    display=f["value"],
                    doc=f["doc"],
                    page=f["page"],
                )
                for f in facts_payload(xray, fields, "en")
            ]

        def pin_objects(ipo_id: str) -> Passage | None:
            try:
                xray = load_xray(settings.paths.processed_dir, ipo_id)
                return objects_passage(xray, retriever.index(ipo_id).passages)
            except FileNotFoundError:
                return None

        return cls(
            search=retriever.search,
            llm=get_llm(settings.llm),
            traces=TraceStore(settings.paths.data_dir / "traces.sqlite"),
            facts=facts,
            budget_chars=max(1500, (settings.llm.num_ctx - 700) * 3),
            pin_objects=pin_objects,
        )

    # ------------------------------------------------------------------------------------
    def events(self, ipo_id: str, question: str, language: Language = "en") -> Iterator[Event]:
        try:
            yield from self._events(ipo_id, question, language)
        except (LLMUnavailable, ReasoningLeak) as exc:
            yield "error", ErrorEvent(code="llm_unavailable", message=str(exc)[:200])
        except Exception as exc:  # the contract has one generic error; details stay in the log
            yield "error", ErrorEvent(code="internal_error", message=type(exc).__name__)

    def _events(self, ipo_id: str, question: str, language: Language) -> Iterator[Event]:
        timings: dict[str, int] = {}
        stages: list[dict[str, object]] = []
        passages_log: list[dict[str, object]] = []
        prompt_text = ""
        checks: list[CheckResult] = []

        def stage(name: str, status: str, ms: int | None = None) -> Event:
            stages.append({"name": name, "status": status, "ms": ms})
            return "stage", StageEvent(name=name, status=status, ms=ms)

        def finish(score: float | None, n_numbers: int) -> Iterator[Event]:
            trace_id = new_trace_id()
            self.traces.save(
                ipo_id,
                Trace(
                    trace_id=trace_id, question=question, stages=stages, passages=passages_log,
                    prompt=prompt_text, checks=checks, timings_ms=dict(timings),
                ),
            )  # fmt: skip
            yield (
                "final",
                FinalEvent(
                    trace_id=trace_id, score=score, n_numbers=n_numbers, timings_ms=dict(timings)
                ),
            )

        # 1. guard
        t0 = time.perf_counter()
        yield stage("guard", "start")
        guard = check_question(question)
        timings["guard"] = _ms(t0)
        yield stage("guard", "end", timings["guard"])
        if guard.blocked:
            # ``forecast`` is a proposed third reason (06 lists advice_intent and privacy): the
            # frontend words a prediction refusal differently. ADR-051, needs Akshat review.
            reason = "forecast" if guard.category == "forecast" else guard.reason or "advice_intent"
            yield "guard", GuardEvent(blocked=True, reason=reason, facts=self.facts(ipo_id))
            yield from finish(None, 0)
            return

        # 2. retrieval
        t0 = time.perf_counter()
        yield stage("retrieving", "start")
        result = self.search(question, ipo_id)
        timings["retrieving"] = _ms(t0)
        yield stage("retrieving", "end", timings["retrieving"])
        hits = result.hits
        pinned = self.pin_objects(ipo_id) if self.pin_objects and wants_objects(question) else None
        if (
            pinned is not None
        ):  # ADR-053: the objects passage answers alone; neighbours only distract
            top = result.top_score if result.top_score is not None else 0.0
            hits = [Hit(pinned, top, 1)]
            result = SearchResult(hits, result.method, False, top, result.notes)
        if result.abstain or not hits:
            closest = hits[0] if hits else None
            ev = AbstainEvent(
                reason="low_retrieval_score",
                closest_passage=_passage_event(
                    1, closest.passage, closest.rank, result.method, closest.score
                ) if closest else None,
            )  # fmt: skip
            if closest:
                passages_log.append(ev.closest_passage.model_dump())  # type: ignore[union-attr]
            yield "abstain", ev
            yield from finish(None, 0)
            return
        prompt = build_prompt(
            question, [h.passage for h in hits], language, budget_chars=self.budget_chars
        )
        prompt_text = prompt.text
        used = {p.id for p in prompt.passages}
        kept = [
            _passage_event(i + 1, h.passage, h.rank, result.method, h.score)
            for i, h in enumerate(h for h in hits if h.passage.id in used)
        ]
        dropped = [
            _passage_event(i + 1, h.passage, h.rank, result.method, h.score)
            for i, h in enumerate(h for h in hits if h.passage.id not in used)
        ]
        passages_log.extend(p.model_dump() | {"dropped": False} for p in kept)
        passages_log.extend(p.model_dump() | {"dropped": True} for p in dropped)
        yield "retrieval", RetrievalEvent(passages=kept, dropped=dropped)

        # 3. generation: respond() blocks, so it runs in a thread and pieces come through a queue
        t0 = time.perf_counter()
        yield stage("generating", "start")
        pieces: queue.Queue[object] = queue.Queue()
        box: dict[str, object] = {}

        def work() -> None:
            try:
                box["response"] = respond(
                    question, language, lambda: [h.passage for h in hits], self.llm,
                    budget_chars=self.budget_chars, max_tokens=self.max_tokens,
                    on_piece=pieces.put,
                )  # fmt: skip
            except BaseException as exc:
                box["error"] = exc
            finally:
                pieces.put(_DONE)

        threading.Thread(target=work, daemon=True).start()
        while (item := pieces.get()) is not _DONE:
            yield "token", TokenEvent(text=str(item))
        if "error" in box:
            raise box["error"]  # type: ignore[misc]
        response = box["response"]
        timings["generating"] = _ms(t0)
        yield stage("generating", "end", timings["generating"])

        status = response.status  # type: ignore[attr-defined]
        if status == "error":
            raise LLMUnavailable(response.error or "language model unavailable")  # type: ignore[attr-defined]
        text: str = response.text  # type: ignore[attr-defined]
        if response.prompt:  # type: ignore[attr-defined]
            prompt_text = response.prompt.text  # type: ignore[attr-defined]
        n_used = len(response.passages)  # type: ignore[attr-defined]
        citations = [
            Citation(n=int(m.group(1)), char_start=m.start(), char_end=m.end())
            for m in _CITATION.finditer(text)
            if 1 <= int(m.group(1)) <= n_used
        ]
        yield "answer", AnswerEvent(text=text, citations=citations)

        # 4. verification: a refused or rejected text (the "not found" sentence) has no numbers
        t0 = time.perf_counter()
        yield stage("verifying", "start")
        verdicts = []
        if status == "answered":
            verdicts = verify_answer(text, response.passages).verdicts  # type: ignore[attr-defined]
        by_id = {p.id: p for p in response.passages}  # type: ignore[attr-defined]
        sent = [e for v in verdicts if (e := verdict_event(v, by_id)) is not None]
        timings["verifying"] = _ms(t0)
        yield stage("verifying", "end", timings["verifying"])
        for e in sent:
            yield "verdict", e
        checks.extend(v.check for v in verdicts)
        score = sum(e.status == "verified" for e in sent) / len(sent) if sent else None
        yield from finish(score, len(sent))


__all__ = ["ChatOrchestrator", "Event", "verdict_event"]
