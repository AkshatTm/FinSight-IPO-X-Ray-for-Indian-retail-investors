"""Ask one question about one IPO and print a cited answer.

    uv run python -m finsight.generate ask --ipo urban-company-2025 "Who is the registrar?"
    uv run python -m finsight.generate ask --ipo urban-company-2025 --lang hi "रजिस्ट्रार कौन है?"

    uv run python -m finsight.generate ask --ipo ather-energy-2025 "How big is the fresh issue?"
        --answer "The fresh issue is ₹ 26,260 crore [1]."      (no model: check this answer)

Retrieve -> prompt -> stream -> verify: every number in the answer gets ✅ / ⚠️ / ❌ against the
retrieved passages (P3.3). ``--answer`` skips the language model and checks the text you give,
which is how the scale trick is shown. The guard runs first (advice, forecasts, privacy): a refused
question prints the refusal and the key X-Ray facts, with no retrieval and no model call.
Generation goes through ``generate.respond`` (the same path as the bake-off and the chat):
the question guard, loop cutting, the output rules and the privacy output filter all apply, and a
rejected answer is replaced by "not found" with the reason shown. Retrieval follows the profile in
``configs/config.yaml``: dense and rerank are used only when the profile turns them on and the
``ml`` group is installed (``uv run --group ml``); otherwise BM25 alone answers.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from finsight.core.config import get_settings, load_settings
from finsight.core.schemas import Passage
from finsight.generate.llm_backend import get_llm
from finsight.generate.prompts import build_prompt, cited_indices
from finsight.generate.respond import respond
from finsight.guard import check_question, facts_payload, refusal_text
from finsight.retrieve import (
    BgeM3Embedder,
    CrossEncoderReranker,
    Embedder,
    Reranker,
    Retriever,
    SearchResult,
)
from finsight.verify import format_verdicts, verify_answer


def _retriever(profile: str | None) -> Retriever:
    settings = load_settings(profile) if profile else get_settings()
    embedder: Embedder | None = None
    reranker: Reranker | None = None
    try:
        if settings.retrieve.dense:
            embedder = BgeM3Embedder()
        if settings.retrieve.rerank:
            reranker = CrossEncoderReranker()
    except ImportError:
        print("(retrieval: ml group not installed, using BM25 only)", file=sys.stderr)
    return Retriever(
        settings.paths.processed_dir,
        embedder=embedder,
        reranker=reranker,
        pool=settings.retrieve.rerank_top_n,
        top_k=settings.retrieve.final_top_k,
    )


def ask(
    ipo_id: str,
    question: str,
    language: str,
    profile: str | None,
    model: str | None,
    given_answer: str | None = None,
) -> int:
    settings = load_settings(profile) if profile else get_settings()
    config = settings.llm.model_copy(update={"model": model}) if model else settings.llm
    retriever = _retriever(profile)
    found: dict[str, SearchResult] = {}

    def retrieve() -> list[Passage]:
        found["result"] = retriever.search(question, ipo_id)
        return [h.passage for h in found["result"].hits]

    if given_answer is not None:  # no model: check the text the user gives
        guard = check_question(question)
        if guard.blocked:
            return _refuse(settings.paths.processed_dir, ipo_id, guard.reason, language)
        prompt = build_prompt(
            question, retrieve(), language,  # type: ignore[arg-type]
            budget_chars=_budget(config.num_ctx),  # type: ignore[arg-type]
        )  # fmt: skip
        print(given_answer)
        print("\nNumbers:")
        print(format_verdicts(verify_answer(given_answer, prompt.passages)))
        return 0
    response = respond(
        question,
        language,  # type: ignore[arg-type]
        retrieve,
        get_llm(config),
        budget_chars=_budget(config.num_ctx),  # type: ignore[arg-type]
    )
    if response.status == "refused":
        return _refuse(
            settings.paths.processed_dir, ipo_id, response.reason, language, response.text
        )
    if response.status == "error":
        print(f"\nThe language model is unavailable: {response.error}", file=sys.stderr)
        return 2 if response.reason == "unavailable" else 3
    if response.reason == "no_passages":
        print("No passage matched the question; nothing to answer from.")
        return 1
    print(response.text)
    if response.status == "rejected":
        print(f"\n[{response.reason}] the model's answer was not usable and was replaced.")
        if response.raw.strip():
            print(f"raw model output: {response.raw.strip()[:300]!r}", file=sys.stderr)
    else:
        notes = [
            note
            for note, on in (
                ("loop trimmed", response.trimmed),
                ("Devanagari digits converted", response.digits_converted),
            )
            if on
        ]
        if notes:
            print(f"\n[{', '.join(notes)}]")
        passages = response.passages
        print("\nSources:")
        for n in cited_indices(response.text, len(passages)):
            p = passages[n - 1]
            print(f"  [{n}] {p.doc_type.upper()} page {p.page_start}  ({p.id})")
        print("\nNumbers:")
        print(format_verdicts(verify_answer(response.text, passages)))
    result = found.get("result")
    dropped = response.prompt.dropped if response.prompt else 0
    print(
        f"\n(retrieval {result.method if result else '-'}; first token "
        f"{response.first_token_s or 0:.1f}s; total {response.total_s:.1f}s; "
        f"{len(response.passages)} passages, {dropped} dropped)",
        file=sys.stderr,
    )
    return 0


def _refuse(
    processed_dir: Path, ipo_id: str, reason: str | None, language: str, text: str | None = None
) -> int:
    print(text or refusal_text(reason or "advice_intent", language))  # type: ignore[arg-type]
    _print_facts(processed_dir, ipo_id, language)
    return 0


def _print_facts(processed_dir: Path, ipo_id: str, language: str) -> None:
    """The key X-Ray facts under a refusal; silent when no X-Ray has been built yet."""
    from finsight.extract import load_fields
    from finsight.pipeline.xray_stage import load_xray

    try:
        xray = load_xray(processed_dir, ipo_id)
    except FileNotFoundError:
        return
    print()
    for fact in facts_payload(xray, load_fields(), language):  # type: ignore[arg-type]
        print(f"  {fact['label']}: {fact['value']}  ({fact['doc'].upper()} p.{fact['page']})")


def _budget(num_ctx: int) -> int:
    """Characters of passages that fit: context minus rules and answer, ~3 chars per token."""
    return max(1500, (num_ctx - 700) * 3)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.generate")
    sub = parser.add_subparsers(dest="command", required=True)
    ask_p = sub.add_parser("ask", help="answer one question with citations")
    ask_p.add_argument("--ipo", required=True)
    ask_p.add_argument("--lang", choices=["en", "hi"], default="en")
    ask_p.add_argument("--profile", help="config profile (default: FINSIGHT_PROFILE or dev_light)")
    ask_p.add_argument("--model", help="override the profile's Ollama model")
    ask_p.add_argument("--answer", help="skip the model and verify this answer text instead")
    ask_p.add_argument("question")
    args = parser.parse_args(argv)
    return ask(args.ipo, args.question, args.lang, args.profile, args.model, args.answer)


if __name__ == "__main__":
    sys.exit(main())
