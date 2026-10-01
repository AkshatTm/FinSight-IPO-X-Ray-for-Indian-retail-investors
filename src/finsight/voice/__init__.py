"""Speech recognition: a faster-whisper backend, lazy loading and error metrics."""

from finsight.voice.asr import FasterWhisperBackend, Transcript
from finsight.voice.manager import IDLE_UNLOAD_S, AsrManager
from finsight.voice.metrics import cer, cer_with_spaces, normalize, wer

__all__ = [
    "IDLE_UNLOAD_S",
    "AsrManager",
    "FasterWhisperBackend",
    "Transcript",
    "cer",
    "cer_with_spaces",
    "normalize",
    "wer",
]
