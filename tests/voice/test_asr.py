from pathlib import Path
from types import SimpleNamespace
from typing import Any

from finsight.voice import FasterWhisperBackend


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def transcribe(self, path: str, **kwargs: Any):  # type: ignore[no-untyped-def]
        self.calls.append({"path": path, **kwargs})
        segments = [SimpleNamespace(text=" इस आईपीओ में "), SimpleNamespace(text="प्रमोटर कौन हैं? ")]
        return iter(segments), SimpleNamespace(duration=4.2)


def backend() -> tuple[FasterWhisperBackend, list[tuple[str, str, str, int]], FakeModel]:
    loads: list[tuple[str, str, str, int]] = []
    model = FakeModel()

    def loader(name: str, device: str, compute: str, threads: int) -> FakeModel:
        loads.append((name, device, compute, threads))
        return model

    return FasterWhisperBackend("small", loader=loader), loads, model


def test_nothing_is_loaded_until_the_first_transcription() -> None:
    asr, loads, _ = backend()
    assert not asr.loaded
    assert loads == []
    asr.transcribe(Path("clip.m4a"))
    assert asr.loaded
    assert loads == [("small", "cpu", "int8", 4)]


def test_transcript_joins_segments_and_passes_hindi() -> None:
    asr, _, model = backend()
    result = asr.transcribe_detailed(Path("clip.m4a"), "hi")
    assert result.text == "इस आईपीओ में प्रमोटर कौन हैं?"
    assert result.duration_s == 4.2
    assert result.model == "small"
    assert model.calls[0]["language"] == "hi"
    assert model.calls[0]["condition_on_previous_text"] is False


def test_load_is_idempotent_and_unload_frees_the_model() -> None:
    asr, loads, _ = backend()
    asr.load()
    assert asr.load() == 0.0
    assert len(loads) == 1
    asr.unload()
    assert not asr.loaded
    asr.transcribe(Path("clip.m4a"))
    assert len(loads) == 2
