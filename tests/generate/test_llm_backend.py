import json
from collections.abc import Iterator
from typing import Any

import pytest

from finsight.core.config import LLMConfig
from finsight.generate.llm_backend import (
    LLMUnavailable,
    OllamaBackend,
    ReasoningLeak,
    get_llm,
)


def lines(*events: dict[str, Any]) -> list[bytes]:
    return [(json.dumps(e) + "\n").encode() for e in events]


def fake(events: list[bytes], seen: list[Any] | None = None):  # type: ignore[no-untyped-def]
    def opener(url: str, body: dict[str, Any], timeout: float) -> Iterator[bytes]:
        if seen is not None:
            seen.append((url, body, timeout))
        yield from events

    return opener


def msg(text: str, done: bool = False) -> dict[str, Any]:
    return {"message": {"role": "assistant", "content": text}, "done": done}


def test_streams_content_pieces_in_order_and_stops_at_done() -> None:
    events = lines(msg("The "), msg("registrar"), msg("", done=True), msg("ignored"))
    backend = OllamaBackend(opener=fake(events))
    assert list(backend.stream("q", max_tokens=50, temperature=0.2, language="en")) == [
        "The ",
        "registrar",
    ]
    assert backend.generate("q") == "The registrar"


def test_request_disables_thinking_and_sets_options() -> None:
    seen: list[Any] = []
    backend = OllamaBackend(
        model="qwen3.5:2b",
        num_ctx=3072,
        host="http://h:1/",
        opener=fake(lines(msg("", True)), seen),
    )
    list(backend.stream("hello", max_tokens=77, temperature=0.1, language="hi"))
    url, body, _ = seen[0]
    assert url == "http://h:1/api/chat"
    assert body["think"] is False
    assert body["stream"] is True
    assert body["model"] == "qwen3.5:2b"
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    assert body["options"] == {
        "num_ctx": 3072,
        "num_predict": 77,
        "temperature": 0.1,
        "repeat_penalty": 1.15,
        "stop": ["DATA>>>", "<<<DATA"],
    }


def test_reasoning_tokens_fail_loudly() -> None:
    thinking = {"message": {"role": "assistant", "content": "", "thinking": "Let me think"}}
    backend = OllamaBackend(opener=fake(lines(thinking, msg("answer", True))))
    with pytest.raises(ReasoningLeak, match="think=false"):
        backend.generate("q")


def test_server_error_event_becomes_llm_unavailable() -> None:
    backend = OllamaBackend(opener=fake(lines({"error": "model 'x' not found"})))
    with pytest.raises(LLMUnavailable, match="not found"):
        backend.generate("q")


def test_unreachable_server_is_llm_unavailable() -> None:
    backend = OllamaBackend(host="http://127.0.0.1:9", timeout=1.0)  # nothing listens on port 9
    with pytest.raises(LLMUnavailable, match="cannot reach"):
        backend.generate("q")
    assert backend.is_available() is False


def test_is_available_checks_the_installed_models() -> None:
    def tags(url: str, timeout: float) -> dict[str, Any]:
        return {"models": [{"name": "qwen3.5:2b"}, {"name": "gemma:latest"}]}

    assert OllamaBackend(model="qwen3.5:2b", tags=tags).is_available() is True
    assert OllamaBackend(model="gemma", tags=tags).is_available() is True
    assert OllamaBackend(model="qwen3.5:9b", tags=tags).is_available() is False


def test_get_llm_follows_the_config() -> None:
    backend = get_llm(LLMConfig(model="qwen3.5:2b", num_ctx=4096))
    assert (backend.model, backend.num_ctx) == ("qwen3.5:2b", 4096)
    with pytest.raises(NotImplementedError, match="ADR-022"):
        get_llm(LLMConfig(backend="llama-cpp"))
