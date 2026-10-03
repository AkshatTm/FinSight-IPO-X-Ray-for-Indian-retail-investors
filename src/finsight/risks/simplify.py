"""Plain-English rewrites of risk factors (B02 §8): prompt contract, post-checks, fallback.

The student (Qwen ~4B, QLoRA on Kaggle, served as GGUF Q4 by llama.cpp) gets ``student_prompt``;
its training pairs use the same prompt (``notebooks/b2_student_qlora_kaggle.ipynb`` is
generated from this module). A rewrite is shown only if it passes the post-checks, in this order:

1. numbers: every number in the rewrite matches one in the original (``risks.checks``);
2. forbidden phrases (``configs/forbidden_phrases.yaml``);
3. length (at most ``MAX_WORDS`` words, the teacher filter's limit);
4. certainty: "may/could" must not become definite, and facts must not gain a hedge.

A failing rewrite is ``rejected`` and the UI shows the original with a note.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from finsight.core.config import SimplifyConfig
from finsight.core.schemas import SimpleStatus
from finsight.guard import find_forbidden
from finsight.risks.certainty import certainty_changed
from finsight.risks.checks import unmatched_numbers, word_count
from finsight.risks.clf_metrics import company_bucket
from finsight.risks.filters import MAX_WORDS
from finsight.risks.teacher_run import read_jsonl

PROMPT_VERSION = "student-v1"
MAX_NEW_TOKENS = 160
CHECKS = ("number_mismatch", "forbidden_phrase", "too_long", "certainty_changed", "empty")

INSTRUCTIONS = """Rewrite this risk factor from an Indian IPO offer document in plain English \
for a first-time investor.
Rules: at most 60 words; sentences under 20 words; keep every number exactly as written, with its \
unit; keep how certain it is ("may" stays "may", "has" stays "has"); add no facts; never tell \
anyone to buy, sell, apply, invest or avoid; never call the IPO good, bad, safe or worth it.
Answer with the rewrite only."""


def student_prompt(title: str, body: str) -> str:
    """The one prompt the student is trained and served with."""
    text = f"Title: {title.strip()}\n\n{body.strip()}" if title.strip() else body.strip()
    return f"{INSTRUCTIONS}\n\nRisk factor:\n{text}"


_PREFIX = re.compile(r"^(?:plain[- ]english(?: version)?|rewrite|simplified)\s*:\s*", re.I)


def clean(raw: str) -> str:
    """Strip quotes, a leading label and surrounding whitespace from a model answer."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    text = _PREFIX.sub("", text).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'“”":
        text = text[1:-1].strip()
    return re.sub(r"\s+", " ", text.replace("“", '"').replace("”", '"'))


def post_check(original: str, rewrite: str) -> tuple[str, str] | None:
    """``(reason, detail)`` for the first failing check, or ``None`` when the rewrite passes."""
    if not rewrite.strip():
        return "empty", ""
    missing = unmatched_numbers(original, rewrite)
    if missing:
        return "number_mismatch", ", ".join(missing)
    hits = find_forbidden(rewrite)
    if hits:
        return "forbidden_phrase", hits[0].id
    n = word_count(rewrite)
    if n > MAX_WORDS:
        return "too_long", str(n)
    changed = certainty_changed(original, rewrite)
    if changed:
        return "certainty_changed", changed
    return None


class TextLLM(Protocol):
    """The ``generate`` part of the LLM backends (Ollama, llama.cpp)."""

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """The model's full reply to ``prompt``."""


@dataclass(frozen=True)
class Rewrite:
    """The result of one rewrite: status, text, reason, model and fallback flag."""

    status: SimpleStatus  # ready | rejected | failed
    simple: str | None  # only when ready
    reason: str = ""  # a CHECKS entry, or "unavailable"/"error" when failed
    detail: str = ""
    model: str = ""
    fallback: bool = False  # the base model answered because the student was unavailable
    seconds: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        """The fields saved in ``simplified.json``."""
        return {
            "simple": self.simple,
            "simple_status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "model": self.model,
            "fallback": self.fallback,
            "seconds": round(self.seconds, 2),
            "prompt_version": PROMPT_VERSION,
        }


class Simplifier:
    """The student, with the base instruct model as a flagged fallback (B02 §8)."""

    def __init__(
        self,
        llm: TextLLM,
        model: str,
        fallback: TextLLM | None = None,
        fallback_model: str = "",
    ) -> None:
        self.llm, self.model = llm, model
        self.fallback, self.fallback_model = fallback, fallback_model

    def _ask(self, prompt: str) -> tuple[str, str, bool]:
        from finsight.generate import LLMUnavailable

        try:
            return (
                self.llm.generate(prompt, max_tokens=MAX_NEW_TOKENS, temperature=0.2),
                self.model,
                False,
            )
        except LLMUnavailable:
            if self.fallback is None:
                raise
        raw = self.fallback.generate(prompt, max_tokens=MAX_NEW_TOKENS, temperature=0.2)
        return raw, self.fallback_model, True

    def rewrite(self, title: str, body: str) -> Rewrite:
        """Ask the model, then run the post-checks; an unavailable model gives ``failed``."""
        from finsight.generate import LLMUnavailable, ReasoningLeak

        original = f"{title}\n\n{body}" if title.strip() else body
        t0 = time.perf_counter()
        try:
            raw, model, fell_back = self._ask(student_prompt(title, body))
        except LLMUnavailable as err:
            return Rewrite("failed", None, "unavailable", str(err)[:200], self.model)
        except ReasoningLeak as err:
            return Rewrite("failed", None, "error", str(err)[:200], self.model)
        seconds = time.perf_counter() - t0
        text = clean(raw)
        problem = post_check(original, text)
        if problem:
            return Rewrite("rejected", None, *problem, model, fell_back, seconds)
        return Rewrite("ready", text, "", "", model, fell_back, seconds)


def _backend(backend: str, model: str, models_dir: Path) -> TextLLM:
    if backend == "llama-cpp":
        from finsight.generate.llama_cpp_backend import LlamaCppBackend

        path = Path(model)
        if not path.is_absolute() and not path.exists():
            path = models_dir / "simplifier" / model
        return LlamaCppBackend(model_path=path, num_ctx=2048)
    from finsight.generate import OllamaBackend

    return OllamaBackend(model=model, num_ctx=2048)


def make_simplifier(cfg: SimplifyConfig, models_dir: Path) -> Simplifier:
    """The simplifier the profile names (``simplify.*``), with its fallback if one is set.

    llama-cpp model names are files in ``<models_dir>/simplifier/`` unless given as a path.
    """
    llm = _backend(cfg.backend, cfg.model, models_dir)
    fallback = None
    if cfg.fallback_model:
        fallback = _backend(cfg.backend, cfg.fallback_model, models_dir)
    return Simplifier(llm, cfg.model, fallback, cfg.fallback_model or "")


# ----------------------------------------------------------------------------- training data
def split_pairs(
    rows: Sequence[dict[str, Any]], dev_fraction: float = 0.05, seed: int = 2026
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Teacher pairs split 95/5 by company (B03 §5)."""
    train, dev = [], []
    for row in rows:
        side = dev if company_bucket(str(row.get("company", "")), seed) < dev_fraction else train
        side.append(row)
    return train, dev


def to_chat(row: dict[str, Any]) -> dict[str, Any]:
    """One SFT example: the serving prompt as the user turn, the teacher rewrite as the answer."""
    original = str(row["original"])
    title, _, body = (
        original.partition("\n\n") if original.startswith("Title: ") else ("", "", original)
    )
    return {
        "risk_id": row["risk_id"],
        "company": row.get("company", ""),
        "messages": [
            {"role": "user", "content": student_prompt(title.removeprefix("Title: "), body)},
            {"role": "assistant", "content": str(row["simple"])},
        ],
    }


def main(argv: list[str] | None = None) -> None:
    """CLI: ``split`` the teacher pairs into train and dev for the student."""
    p = argparse.ArgumentParser(prog="python -m finsight.risks.simplify")
    p.add_argument("command", choices=["split"])
    p.add_argument("--pairs", type=Path, default=Path("data/processed/teacher/simplify.jsonl"))
    p.add_argument("--out", type=Path, default=Path("data/processed/kaggle/simplify"))
    args = p.parse_args(argv)
    train, dev = split_pairs(list(read_jsonl(args.pairs)))
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("dev", dev)):
        with (args.out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(to_chat(row), ensure_ascii=False) + "\n")
    print(f"train {len(train)} dev {len(dev)} -> {args.out}")


if __name__ == "__main__":
    main()
