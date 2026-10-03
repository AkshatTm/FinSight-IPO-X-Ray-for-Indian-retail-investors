import json
from pathlib import Path
from typing import Any

import pytest

from finsight.core.config import SimplifyConfig
from finsight.generate import LLMUnavailable, ReasoningLeak
from finsight.risks.simplify import (
    PROMPT_VERSION,
    Simplifier,
    clean,
    main,
    make_simplifier,
    post_check,
    split_pairs,
    student_prompt,
    to_chat,
)

TITLE = "We depend on a few customers"
BODY = (
    "Our top ten customers contributed 62.48% of our revenue from operations in Fiscal 2024. "
    "The loss of any of them may adversely affect our business."
)
ORIGINAL = f"{TITLE}\n\n{BODY}"
GOOD = "Ten customers gave 62.48% of revenue in Fiscal 2024. Losing one may hurt the business."


class Fake:
    def __init__(self, answer: str | Exception) -> None:
        self.answer, self.prompts = answer, []  # type: ignore[var-annotated]

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.prompts.append(prompt)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_prompt_carries_the_rules_and_the_text() -> None:
    p = student_prompt(TITLE, BODY)
    assert "at most 60 words" in p
    assert p.endswith(f"Risk factor:\nTitle: {TITLE}\n\n{BODY}")
    assert student_prompt("", "Body.").endswith("Risk factor:\nBody.")


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        (f'"{GOOD}"', GOOD),
        (f"Plain English: {GOOD}", GOOD),
        (f"<think>x</think>\n  {GOOD}  ", GOOD),
        ("a\n\nb", "a b"),
    ],
)
def test_clean(raw: str, want: str) -> None:
    assert clean(raw) == want


@pytest.mark.parametrize(
    ("rewrite", "reason"),
    [
        (GOOD, None),
        ("", "empty"),
        ("Ten customers gave 65% of revenue; losing one may hurt.", "number_mismatch"),
        ("Losing a customer may hurt, so you should avoid this IPO.", "forbidden_phrase"),
        ("Losing a customer may hurt. " + "more " * 70, "too_long"),
        ("Losing a customer will hurt the business.", "certainty_changed"),
    ],
)
def test_post_checks_run_in_order(rewrite: str, reason: str | None) -> None:
    got = post_check(ORIGINAL, rewrite)
    assert (got[0] if got else None) == reason


def test_ready_rewrite_and_trace_fields() -> None:
    llm = Fake(f'"{GOOD}"')
    r = Simplifier(llm, "student").rewrite(TITLE, BODY)
    assert r.status == "ready"
    assert r.simple == GOOD
    assert r.fallback is False
    assert llm.prompts == [student_prompt(TITLE, BODY)]
    d = r.as_dict()
    assert d["simple_status"] == "ready"
    assert d["prompt_version"] == PROMPT_VERSION


def test_rejected_rewrite_keeps_no_text() -> None:
    r = Simplifier(Fake("Losing one will hurt."), "student").rewrite(TITLE, BODY)
    assert r.status == "rejected"
    assert r.simple is None
    assert r.reason == "certainty_changed"


def test_fallback_is_used_and_flagged_when_the_student_is_missing() -> None:
    s = Simplifier(Fake(LLMUnavailable("no file")), "student", Fake(GOOD), "base")
    r = s.rewrite(TITLE, BODY)
    assert r.status == "ready"
    assert r.model == "base"
    assert r.fallback is True


def test_failures_without_a_fallback() -> None:
    r = Simplifier(Fake(LLMUnavailable("down")), "student").rewrite(TITLE, BODY)
    assert r.status == "failed"
    assert r.reason == "unavailable"
    r = Simplifier(Fake(ReasoningLeak("think")), "student").rewrite(TITLE, BODY)
    assert r.status == "failed"
    assert r.reason == "error"


def test_make_simplifier_picks_backends(tmp_path: Path) -> None:
    s = make_simplifier(
        SimplifyConfig(backend="llama-cpp", model="s.gguf", fallback_model="b.gguf"), tmp_path
    )
    assert s.llm.model_path == tmp_path / "simplifier" / "s.gguf"  # type: ignore[attr-defined]
    assert s.fallback is not None
    assert s.fallback_model == "b.gguf"
    assert s.fallback is not None
    assert make_simplifier(SimplifyConfig(), tmp_path).llm.model == "qwen3.5:2b"  # type: ignore[attr-defined]


def test_a_missing_gguf_file_fails_cleanly(tmp_path: Path) -> None:
    s = make_simplifier(SimplifyConfig(backend="llama-cpp", model="none.gguf"), tmp_path)
    assert s.rewrite(TITLE, BODY).reason == "unavailable"


def test_training_pairs_split_by_company_and_use_the_serving_prompt(tmp_path: Path) -> None:
    rows = [
        {
            "risk_id": f"r{i}",
            "company": f"Co {i}",
            "original": f"Title: {TITLE}\n\n{BODY}",
            "simple": GOOD,
        }
        for i in range(200)
    ]
    train, dev = split_pairs(rows)
    assert not {r["company"] for r in train} & {r["company"] for r in dev}
    assert 0 < len(dev) < 30
    chat = to_chat(rows[0])
    assert chat["messages"][0]["content"] == student_prompt(TITLE, BODY)
    assert chat["messages"][1] == {"role": "assistant", "content": GOOD}
    untitled = to_chat({"risk_id": "x", "original": BODY, "simple": GOOD})
    assert untitled["messages"][0]["content"] == student_prompt("", BODY)
    pairs = tmp_path / "simplify.jsonl"
    pairs.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    main(["split", "--pairs", str(pairs), "--out", str(tmp_path / "k")])
    n = sum(1 for _ in (tmp_path / "k" / "train.jsonl").open()) + sum(
        1 for _ in (tmp_path / "k" / "dev.jsonl").open()
    )
    assert n == 200
