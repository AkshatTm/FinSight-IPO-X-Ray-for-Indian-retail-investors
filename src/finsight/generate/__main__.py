"""Ask one question about one IPO and print a cited answer.

    uv run python -m finsight.generate ask --ipo urban-company-2025 "Who is the registrar?"
    uv run python -m finsight.generate ask --ipo urban-company-2025 --lang hi "रजिस्ट्रार कौन है?"

This is the P3.2 slice of the chat pipeline (retrieve -> prompt -> stream); the guard and the
number verifier join in P3.3-P3.6 (``finsight.chat``). Retrieval follows the profile in
``configs/config.yaml``: dense and rerank are used only when the profile turns them on and the
``ml`` group is installed (``uv run --group ml``); otherwise BM25 alone answers.
"""

from __future__ import annotations

import argparse
import sys
import time

from finsight.core.config import get_settings, load_settings
from finsight.generate.llm_backend import LLMUnavailable, ReasoningLeak, get_llm
from finsight.generate.prompts import build_prompt, cited_indices, is_not_found
from finsight.retrieve import BgeM3Embedder, CrossEncoderReranker, Embedder, Reranker, Retriever


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


def ask(ipo_id: str, question: str, language: str, profile: str | None, model: str | None) -> int:
    settings = load_settings(profile) if profile else get_settings()
    config = settings.llm.model_copy(update={"model": model}) if model else settings.llm
    llm = get_llm(config)
    started = time.perf_counter()
    result = _retriever(profile).search(question, ipo_id)
    retrieved = time.perf_counter()
    if not result.hits:
        print("No passage matched the question; nothing to answer from.")
        return 1
    prompt = build_prompt(
        question,
        [h.passage for h in result.hits],
        language,
        budget_chars=_budget(config.num_ctx),  # type: ignore[arg-type]
    )
    answer: list[str] = []
    first: float | None = None
    try:
        for piece in llm.stream(prompt.text, max_tokens=300, temperature=0.2, language=language):  # type: ignore[arg-type]
            first = first or time.perf_counter()
            answer.append(piece)
            print(piece, end="", flush=True)
    except LLMUnavailable as exc:
        print(f"\nThe language model is unavailable: {exc}", file=sys.stderr)
        return 2
    except ReasoningLeak as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 3
    done = time.perf_counter()
    text = "".join(answer)
    print()
    if not is_not_found(text, language):  # type: ignore[arg-type]
        print("\nSources:")
        for n in cited_indices(text, len(prompt.passages)):
            p = prompt.passages[n - 1]
            print(f"  [{n}] {p.doc_type.upper()} page {p.page_start}  ({p.id})")
    print(
        f"\n(retrieval {result.method} {retrieved - started:.1f}s; first token "
        f"{(first or done) - retrieved:.1f}s; total {done - started:.1f}s; "
        f"{len(prompt.passages)} passages, {prompt.dropped} dropped)",
        file=sys.stderr,
    )
    return 0


def _budget(num_ctx: int) -> int:
    """Characters of passages that fit: context minus rules and answer, ~3 chars per token."""
    return max(1500, (num_ctx - 650) * 3)


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
    ask_p.add_argument("question")
    args = parser.parse_args(argv)
    return ask(args.ipo, args.question, args.lang, args.profile, args.model)


if __name__ == "__main__":
    sys.exit(main())
