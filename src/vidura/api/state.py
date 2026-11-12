"""Everything the routes share: settings, the IPO store, traces, models, the demo cache.

``get_state`` is a FastAPI dependency; tests override it with a state built on temporary files
and fakes. Heavy parts (the chat orchestrator with its retriever, the ASR model) are built on
first use so that ``/api/health`` and the read-only routes answer at once after start-up.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from vidura import __version__
from vidura.api.demo import DemoCache
from vidura.api.ipos import IpoStore
from vidura.api.models import HealthResponse, ModelStatus
from vidura.chat import ChatOrchestrator, TraceStore
from vidura.core.config import Settings, get_settings
from vidura.generate.llm_backend import DEFAULT_HOST

OLLAMA_PS = f"{DEFAULT_HOST}/api/ps"  # a status probe only: no model is called from here


def _git_sha(root: Path) -> str | None:
    head = root / ".git" / "HEAD"
    try:
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref: "):
            ref = (root / ".git" / ref[5:]).read_text(encoding="utf-8").strip()
        return ref[:7]
    except OSError:
        return None


def _ollama_loaded(model: str, timeout: float = 0.5) -> bool | None:
    """True/False when Ollama answers, None when it is not running."""
    try:
        with urllib.request.urlopen(OLLAMA_PS, timeout=timeout) as response:
            running: list[dict[str, Any]] = json.load(response).get("models", [])
    except (OSError, ValueError):
        return None
    return any(m.get("name") == model or m.get("model") == model for m in running)


@dataclass
class ModelManager:
    """What is loaded right now, for ``/api/health``. It loads nothing itself."""

    settings: Settings
    state: AppState

    def health(self) -> HealthResponse:
        """Status for ``/api/health``: ok, warming (LLM loading) or degraded."""
        s = self.settings
        llm = _ollama_loaded(s.llm.model)
        built = self.state._chat is not None
        if s.demo_mode:
            status = "ok"  # recorded answers need no model
        elif llm is None:
            status = "degraded"
        else:
            status = "ok" if llm else "warming"
        return HealthResponse(
            status=status,
            profile=s.profile,
            demo_mode=s.demo_mode,
            models={
                "llm": ModelStatus(name=s.llm.model, loaded=bool(llm)),
                "dense": ModelStatus(loaded=bool(s.retrieve.dense and built)),
                "reranker": ModelStatus(loaded=bool(s.retrieve.rerank and built)),
            },
            version=__version__,
            git_sha=_git_sha(s.root),
        )


@dataclass
class AppState:
    """Process-wide state for the Phase 1 routes; models are built on first use."""

    settings: Settings
    store: IpoStore
    traces: TraceStore
    demo: DemoCache
    _chat: ChatOrchestrator | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)
    models: ModelManager = field(init=False)

    def __post_init__(self) -> None:
        self.models = ModelManager(self.settings, self)

    def chat(self) -> ChatOrchestrator:
        """The chat orchestrator, built once on first use."""
        with self._lock:
            if self._chat is None:
                self._chat = ChatOrchestrator.from_settings(self.settings.profile)
                self._chat.traces = self.traces  # one trace database for the whole app
            return self._chat


@lru_cache(maxsize=1)
def get_state() -> AppState:
    """The cached app state (a FastAPI dependency)."""
    from vidura.extract import load_fields

    settings = get_settings()
    return AppState(
        settings=settings,
        store=IpoStore(
            settings.paths.processed_dir,
            load_fields(),
            settings.root / settings.storage.local_dir / "docs",
        ),
        traces=TraceStore(settings.paths.data_dir / "traces.sqlite"),
        demo=DemoCache(settings.paths.data_dir / "demo_cache"),
    )
