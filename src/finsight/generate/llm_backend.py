"""The local LLM through Ollama's HTTP API, streamed token by token.

Thinking mode is always off (ADR-032): the request carries ``think: false``, and if the server
sends any reasoning text anyway the stream raises ``ReasoningLeak`` instead of silently spending
seconds on hidden tokens. The HTTP call goes through an injectable ``opener`` so tests run without
a server; the default uses only the standard library.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any, Literal

from finsight.core.config import LLMConfig
from finsight.core.registry import register

DEFAULT_HOST = "http://localhost:11434"
Opener = Callable[[str, dict[str, Any], float], Iterator[bytes]]


class LLMUnavailable(RuntimeError):
    """Ollama is not running, or the model is not installed."""


class ReasoningLeak(RuntimeError):
    """The model produced reasoning tokens although thinking is disabled."""


def _urllib_opener(url: str, body: dict[str, Any], timeout: float) -> Iterator[bytes]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            yield from response
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise LLMUnavailable(f"Ollama answered {exc.code}: {detail}") from exc
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        raise LLMUnavailable(f"cannot reach Ollama at {url}: {exc}") from exc


@register("llm", "ollama")
class OllamaBackend:
    name = "ollama"

    def __init__(
        self,
        model: str = "qwen3.5:0.8b",
        num_ctx: int = 2048,
        host: str = DEFAULT_HOST,
        timeout: float = 120.0,
        keep_alive: str = "10m",
        opener: Opener | None = None,
        tags: Callable[[str, float], dict[str, Any]] | None = None,
    ) -> None:
        self.model, self.num_ctx, self.host = model, num_ctx, host.rstrip("/")
        self.timeout, self.keep_alive = timeout, keep_alive
        self._open = opener or _urllib_opener
        self._tags = tags or _get_json

    @classmethod
    def from_config(cls, config: LLMConfig, **kwargs: Any) -> OllamaBackend:
        return cls(model=config.model, num_ctx=config.num_ctx, **kwargs)

    def request_body(self, prompt: str, max_tokens: int, temperature: float) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "think": False,  # ADR-032
            "keep_alive": self.keep_alive,
            "options": {
                "num_ctx": self.num_ctx,
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

    def stream(
        self,
        prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.2,
        language: Literal["en", "hi"] = "en",
    ) -> Iterator[str]:
        body = self.request_body(prompt, max_tokens, temperature)
        for raw in self._open(f"{self.host}/api/chat", body, self.timeout):
            line = raw.strip()
            if not line:
                continue
            event = json.loads(line)
            if event.get("error"):
                raise LLMUnavailable(str(event["error"]))
            message = event.get("message") or {}
            if message.get("thinking"):
                raise ReasoningLeak(f"{self.model} emitted reasoning tokens with think=false")
            if message.get("content"):
                yield message["content"]
            if event.get("done"):
                return

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return "".join(self.stream(prompt, **kwargs))

    def is_available(self) -> bool:
        """True when the server answers and the model is installed."""
        try:
            tags = self._tags(f"{self.host}/api/tags", 5.0)
        except (LLMUnavailable, ValueError):
            return False
        names = {m["name"] for m in tags.get("models", [])}
        return self.model in names or f"{self.model}:latest" in names


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data: dict[str, Any] = json.loads(response.read())
            return data
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        raise LLMUnavailable(f"cannot reach Ollama at {url}: {exc}") from exc


def get_llm(config: LLMConfig, **kwargs: Any) -> OllamaBackend:
    """The backend the config names. ``llama-cpp`` arrives with the deploy profile (ADR-022)."""
    if config.backend != "ollama":
        raise NotImplementedError(f"LLM backend {config.backend!r} is not built yet (ADR-022)")
    return OllamaBackend.from_config(config, **kwargs)
