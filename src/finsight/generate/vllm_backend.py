"""An OpenAI-compatible vLLM server (optional GPU path, ``cloud_gpu`` profile, B02 §10).

Same contract as the Ollama and llama.cpp backends (``stream``, ``generate``, ``is_available``).
The GPU job starts ``vllm serve`` next to the worker and points ``simplify.vllm_url`` at it;
thinking stays off (``chat_template_kwargs.enable_thinking = false``, ADR-032). The HTTP call
goes through an injectable ``opener`` so tests run without a server; standard library only.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any, Literal

from finsight.core.registry import register
from finsight.generate.llm_backend import STOP, LLMUnavailable, ReasoningLeak

Opener = Callable[[str, dict[str, Any] | None, float], Iterator[bytes]]


def _urllib_opener(url: str, body: dict[str, Any] | None, timeout: float) -> Iterator[bytes]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            yield from response
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise LLMUnavailable(f"vLLM answered {exc.code}: {detail}") from exc
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        raise LLMUnavailable(f"cannot reach vLLM at {url}: {exc}") from exc


@register("llm", "vllm")
class VllmBackend:
    name = "vllm"

    def __init__(
        self, base_url: str, model: str, timeout: float = 120.0, opener: Opener | None = None
    ) -> None:
        self.base_url, self.model, self.timeout = base_url.rstrip("/"), model, timeout
        self._open = opener or _urllib_opener

    def request_body(self, prompt: str, max_tokens: int, temperature: float) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": STOP,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},  # ADR-032
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
        for raw in self._open(f"{self.base_url}/v1/chat/completions", body, self.timeout):
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                return
            event = json.loads(payload)
            if event.get("error"):
                raise LLMUnavailable(str(event["error"]))
            delta = (event.get("choices") or [{}])[0].get("delta") or {}
            if delta.get("reasoning_content") or "<think>" in (delta.get("content") or ""):
                raise ReasoningLeak(f"{self.model} emitted reasoning tokens with thinking off")
            if delta.get("content"):
                yield delta["content"]

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return "".join(self.stream(prompt, **kwargs))

    def is_available(self) -> bool:
        """True when the server answers and serves this model."""
        try:
            raw = b"".join(self._open(f"{self.base_url}/v1/models", None, 5.0))
            models = json.loads(raw.decode("utf-8")).get("data", [])
        except (LLMUnavailable, ValueError):
            return False
        return any(m.get("id") == self.model for m in models)
