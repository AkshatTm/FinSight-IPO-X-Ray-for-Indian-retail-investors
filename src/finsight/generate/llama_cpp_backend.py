"""The deploy LLM: a small GGUF model on CPU through llama-cpp-python (ADR-022, P6.1).

Same contract as the Ollama backend (``stream``, ``generate``, ``is_available``), so the chat
orchestrator does not know which one it has. The model file comes from ``FINSIGHT_GGUF`` (a path)
or from ``llm.model`` in the config when that is a path to an existing file; the file is not in
the repository (the artifact bundle puts it on the Space). ``llama_cpp`` is imported only when the
model is first used, so laptops and CI without the wheel can import this module.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Literal

from finsight.core.config import LLMConfig
from finsight.core.registry import register
from finsight.generate.llm_backend import REPEAT_PENALTY, STOP, LLMUnavailable, ReasoningLeak

ENV_PATH = "FINSIGHT_GGUF"
Loader = Callable[..., Any]


def _load_llama(**kwargs: Any) -> Any:
    try:
        from llama_cpp import Llama
    except ImportError as exc:  # pragma: no cover - depends on the wheel
        raise LLMUnavailable("llama-cpp-python is not installed (deploy image only)") from exc
    return Llama(**kwargs)


@register("llm", "llama-cpp")
class LlamaCppBackend:
    name = "llama-cpp"

    def __init__(
        self,
        model_path: str | Path,
        num_ctx: int = 2048,
        n_threads: int | None = None,
        loader: Loader | None = None,
    ) -> None:
        self.model_path, self.num_ctx = Path(model_path), num_ctx
        self.n_threads = n_threads or os.cpu_count() or 2
        self._loader = loader or _load_llama
        self._llm: Any = None

    @classmethod
    def from_config(cls, config: LLMConfig, **kwargs: Any) -> LlamaCppBackend:
        path = os.environ.get(ENV_PATH) or config.model
        return cls(model_path=path, num_ctx=config.num_ctx, **kwargs)

    def _model(self) -> Any:
        if self._llm is None:
            if not self.model_path.is_file():
                raise LLMUnavailable(f"GGUF file not found: {self.model_path} (set {ENV_PATH})")
            self._llm = self._loader(
                model_path=str(self.model_path),
                n_ctx=self.num_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
        return self._llm

    def stream(
        self,
        prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.2,
        language: Literal["en", "hi"] = "en",
    ) -> Iterator[str]:
        chunks = self._model().create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            repeat_penalty=REPEAT_PENALTY,
            stop=STOP,
            stream=True,
        )
        for chunk in chunks:
            text = (chunk["choices"][0].get("delta") or {}).get("content")
            if not text:
                continue
            if "<think>" in text:  # thinking stays off (ADR-032)
                raise ReasoningLeak(f"{self.model_path.name} emitted reasoning tokens")
            yield text

    def generate(self, prompt: str, **kwargs: Any) -> str:
        return "".join(self.stream(prompt, **kwargs))

    def is_available(self) -> bool:
        """True when the model file exists; the model itself loads on first use."""
        return self.model_path.is_file()
