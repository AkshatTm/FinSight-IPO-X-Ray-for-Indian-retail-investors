"""Speech recognition with faster-whisper (CTranslate2), CPU int8, loaded on first use.

``FasterWhisperBackend`` implements ``core.interfaces.ASRBackend`` (``transcribe``) and adds
``load`` / ``unload`` / ``transcribe_detailed`` so that ``voice.manager.AsrManager`` can keep the
model out of memory until the first voice question and drop it again when idle (ADR-021: an ASR
model is 0.5-1.6 GB, and the laptop has about 8 GB free).

The ``faster_whisper`` import and the model download happen inside ``load``, so importing this
module costs nothing and the ``asr`` dependency group is only needed when a voice question arrives.
``loader`` is injectable so that tests run without a model.
"""

from __future__ import annotations

import gc
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finsight.core.registry import register

DEFAULT_MODEL = "small"
Loader = Callable[[str, str, str, int], Any]


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str
    duration_s: float  # length of the audio, as the model reports it
    seconds: float  # time spent transcribing (not loading)
    model: str


def _faster_whisper_loader(model: str, device: str, compute_type: str, threads: int) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(model, device=device, compute_type=compute_type, cpu_threads=threads)


@register("asr", "faster-whisper")
class FasterWhisperBackend:
    name = "faster-whisper"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
        beam_size: int = 5,
        loader: Loader | None = None,
    ) -> None:
        self.model_name, self.device, self.compute_type = model, device, compute_type
        self.cpu_threads, self.beam_size = cpu_threads, beam_size
        self._loader = loader or _faster_whisper_loader
        self._model: Any = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> float:
        """Load the model unless it is loaded; returns the seconds the load took (0 if loaded)."""
        if self._model is not None:
            return 0.0
        started = time.perf_counter()
        self._model = self._loader(
            self.model_name, self.device, self.compute_type, self.cpu_threads
        )
        return time.perf_counter() - started

    def unload(self) -> None:
        self._model = None
        gc.collect()

    def transcribe_detailed(self, audio_path: Path, language: str = "hi") -> Transcript:
        self.load()
        started = time.perf_counter()
        segments, info = self._model.transcribe(
            str(audio_path),
            language=language,
            beam_size=self.beam_size,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return Transcript(
            text=text,
            language=language,
            duration_s=float(getattr(info, "duration", 0.0)),
            seconds=time.perf_counter() - started,
            model=self.model_name,
        )

    def transcribe(self, audio_path: Path, language: str = "hi") -> str:
        return self.transcribe_detailed(audio_path, language).text
