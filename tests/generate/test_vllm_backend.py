import json
from collections.abc import Iterator
from typing import Any

import pytest

from finsight.generate.llm_backend import LLMUnavailable, ReasoningLeak
from finsight.generate.vllm_backend import VllmBackend


def sse(*deltas: dict[str, Any]) -> list[bytes]:
    lines = [b": keep-alive\n"]
    for d in deltas:
        lines.append(f"data: {json.dumps({'choices': [{'delta': d}]})}\n".encode())
    return [*lines, b"data: [DONE]\n"]


class Opener:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines, self.calls = lines, []  # type: ignore[var-annotated]

    def __call__(self, url: str, body: dict[str, Any] | None, timeout: float) -> Iterator[bytes]:
        self.calls.append((url, body))
        yield from self.lines


def test_streams_content_and_turns_thinking_off() -> None:
    opener = Opener(sse({"role": "assistant"}, {"content": "Ten "}, {"content": "customers."}))
    llm = VllmBackend("http://gpu:8000/", "student", opener=opener)
    assert llm.generate("p", max_tokens=50) == "Ten customers."
    url, body = opener.calls[0]
    assert url == "http://gpu:8000/v1/chat/completions"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["max_tokens"] == 50
    assert body["model"] == "student"


def test_reasoning_and_errors_raise() -> None:
    with pytest.raises(ReasoningLeak):
        VllmBackend("u", "m", opener=Opener(sse({"reasoning_content": "hmm"}))).generate("p")
    bad = Opener([b'data: {"error": "boom"}\n'])
    with pytest.raises(LLMUnavailable, match="boom"):
        VllmBackend("u", "m", opener=bad).generate("p")


def test_is_available_checks_the_model_list() -> None:
    models = [json.dumps({"data": [{"id": "student"}]}).encode()]
    assert VllmBackend("u", "student", opener=Opener(models)).is_available()
    assert not VllmBackend("u", "other", opener=Opener(models)).is_available()

    def down(url: str, body: Any, timeout: float) -> Iterator[bytes]:
        raise LLMUnavailable("down")
        yield b""

    assert not VllmBackend("u", "student", opener=down).is_available()
