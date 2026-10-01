"""Load the ASR model on the first voice question, unload it after ``idle_s`` of silence.

The API's ModelManager (P4.1) owns one ``AsrManager`` and reports ``status()`` in ``/health``
(``{"loaded": false, "lazy": true}`` until the first voice question). ``unload_if_idle`` is the
whole policy and takes the clock from the caller, so it is tested without waiting; ``start`` runs
it on a daemon thread every ``poll_s`` seconds. A transcription in progress holds the lock, so a
model is never unloaded under a running request.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from finsight.voice.asr import Transcript

IDLE_UNLOAD_S = 120.0  # config: voice.idle_unload_s


class LoadableASR(Protocol):
    @property
    def loaded(self) -> bool: ...

    def load(self) -> float: ...

    def unload(self) -> None: ...

    def transcribe_detailed(self, audio_path: Path, language: str = "hi") -> Transcript: ...


class AsrManager:
    def __init__(
        self,
        backend: LoadableASR,
        idle_s: float = IDLE_UNLOAD_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.backend, self.idle_s, self._clock = backend, idle_s, clock
        self._lock = threading.Lock()
        self._last_used: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.loads = 0  # how many times the model was (re)loaded: a cold start is a visible delay

    def transcribe(self, audio_path: Path, language: str = "hi") -> Transcript:
        with self._lock:
            if not self.backend.loaded:
                self.backend.load()
                self.loads += 1
            try:
                return self.backend.transcribe_detailed(audio_path, language)
            finally:
                self._last_used = self._clock()

    def unload_if_idle(self) -> bool:
        """Unload when the model has been unused for ``idle_s``; True if it was unloaded."""
        with self._lock:
            if not self.backend.loaded or self._last_used is None:
                return False
            if self._clock() - self._last_used < self.idle_s:
                return False
            self.backend.unload()
            return True

    def status(self) -> dict[str, object]:
        idle = None if self._last_used is None else round(self._clock() - self._last_used, 1)
        return {"loaded": self.backend.loaded, "lazy": True, "idle_s": idle, "loads": self.loads}

    def start(self, poll_s: float = 10.0) -> None:
        """Check for idleness every ``poll_s`` seconds on a daemon thread."""
        if self._thread is not None:
            return
        self._stop.clear()

        def watch() -> None:
            while not self._stop.wait(poll_s):
                self.unload_if_idle()

        self._thread = threading.Thread(target=watch, name="asr-idle-unload", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
