from pathlib import Path

import pytest

from finsight.generate import LLMUnavailable, ReasoningLeak
from finsight.generate.llama_cpp_backend import LlamaCppBackend


class FakeLlama:
    def __init__(self, pieces: list[str]) -> None:
        self.pieces, self.calls = pieces, []

    def create_chat_completion(self, **kwargs: object):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        for piece in self.pieces:
            yield {"choices": [{"delta": {"content": piece}}]}
        yield {"choices": [{"delta": {}}]}  # the closing chunk has no content


def backend(tmp_path: Path, pieces: list[str]) -> tuple[LlamaCppBackend, FakeLlama]:
    gguf = tmp_path / "m.gguf"
    gguf.write_bytes(b"x")
    fake = FakeLlama(pieces)
    loaded: dict[str, object] = {}

    def loader(**kwargs: object) -> FakeLlama:
        loaded.update(kwargs)
        return fake

    b = LlamaCppBackend(gguf, num_ctx=1024, n_threads=3, loader=loader)
    b.loaded = loaded  # type: ignore[attr-defined]
    return b, fake


def test_streams_the_pieces_and_passes_the_same_limits_as_ollama(tmp_path: Path) -> None:
    b, fake = backend(tmp_path, ["The ", "issue [1]"])
    assert list(b.stream("q", max_tokens=50, temperature=0.1)) == ["The ", "issue [1]"]
    call = fake.calls[0]
    assert (call["max_tokens"], call["temperature"], call["stream"]) == (50, 0.1, True)
    assert "DATA>>>" in call["stop"]  # type: ignore[operator]
    assert b.loaded["n_ctx"] == 1024  # type: ignore[attr-defined]


def test_the_model_loads_once_and_only_on_first_use(tmp_path: Path) -> None:
    b, _ = backend(tmp_path, ["a"])
    assert b.loaded == {}  # type: ignore[attr-defined]
    b.generate("q")
    first = b._llm
    b.generate("q")
    assert b._llm is first


def test_a_missing_model_file_is_unavailable_not_a_crash(tmp_path: Path) -> None:
    b = LlamaCppBackend(tmp_path / "nope.gguf")
    assert b.is_available() is False
    with pytest.raises(LLMUnavailable, match="GGUF"):
        b.generate("q")


def test_reasoning_tokens_are_refused(tmp_path: Path) -> None:
    b, _ = backend(tmp_path, ["<think>hmm"])
    with pytest.raises(ReasoningLeak):
        b.generate("q")
