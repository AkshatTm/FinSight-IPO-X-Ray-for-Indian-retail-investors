"""Preflight (CC-04): are the models an analysis needs there, before the job starts?

An analysis that quietly runs without its models gives a thin report that looks complete (the
Jio upload had 12 of 13 red flags "Not available" for another reason, but a half-served report
is the same trap). So every analysis job first checks the models its stages use; a missing one
refuses the job with a plain message, unless the user ticked "analyse without <model>" (stored
on the document, and the result is then ``degraded``).

Checks are cheap: the small ONNX classifier is really loaded; the large embedder and reranker are
checked by their weights being on disk, not loaded (a 16 GB laptop loads them one stage at a time).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from finsight.core.config import Settings
from finsight.generate.llm_backend import DEFAULT_HOST

OLLAMA_HOST = DEFAULT_HOST
MODELS = ("ollama", "classifier", "embeddings", "reranker")
BGE_M3 = "BAAI/bge-m3"
BGE_RERANKER = "BAAI/bge-reranker-v2-m3"

# What a reader sees when a model is missing, and what ticking "analyse without it" costs.
LABELS: dict[str, str] = {
    "ollama": "the plain-English writer (Ollama, finsight-student)",
    "classifier": "the risk classifier",
    "embeddings": "the novelty embeddings (bge-m3)",
    "reranker": "the answer reranker",
}
# Stages that cannot run without a model; the runner marks them skipped when it is ticked off.
STAGES_NEEDING: dict[str, tuple[str, ...]] = {
    "ollama": ("simplify",),
    "classifier": ("risks_scored",),
}
Probe = Callable[[Settings], "tuple[bool, str]"]


@dataclass(frozen=True)
class Check:
    """One model's result: ``detail`` says what is wrong, or what was found."""

    model: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PreflightResult:
    """All checks of one run. ``blocking`` are the failures the user did not skip."""

    checks: list[Check]
    skipped: frozenset[str] = frozenset()
    blocking: list[Check] = field(init=False)

    def __post_init__(self) -> None:
        blocking = [c for c in self.checks if not c.ok and c.model not in self.skipped]
        object.__setattr__(self, "blocking", blocking)

    @property
    def ok(self) -> bool:
        """True when nothing blocks the job."""
        return not self.blocking

    @property
    def missing(self) -> list[str]:
        """Every failed model, skipped or not."""
        return [c.model for c in self.checks if not c.ok]

    def message(self) -> str:
        """The refusal text, one clause per blocking model."""
        parts = [f"{LABELS[c.model]} ({c.detail})" for c in self.blocking]
        return "Can't analyse right now: " + "; ".join(parts) + "."


def _ollama_tags(host: str = OLLAMA_HOST, timeout: float = 5.0) -> list[dict[str, Any]]:
    with urllib.request.urlopen(f"{host}/api/tags", timeout=timeout) as response:
        models: list[dict[str, Any]] = json.loads(response.read()).get("models", [])
    return models


def ollama_digest(settings: Settings) -> str | None:
    """The installed digest of the student tag, or ``None`` when Ollama or the tag is missing."""
    tag = settings.simplify.model
    try:
        tags = _ollama_tags()
    except (urllib.error.URLError, ConnectionError, TimeoutError, ValueError, OSError):
        return None
    for item in tags:
        if item.get("name") in (tag, f"{tag}:latest"):
            digest = item.get("digest")
            return str(digest) if digest else None
    return None


def _check_ollama(settings: Settings) -> tuple[bool, str]:
    tag = settings.simplify.model
    try:
        tags = _ollama_tags()
    except (urllib.error.URLError, ConnectionError, TimeoutError, ValueError, OSError):
        return False, f"Ollama is not running at {OLLAMA_HOST}"
    names = {str(m.get("name")) for m in tags}
    if tag in names or f"{tag}:latest" in names:
        return True, tag
    return False, f"Ollama has no model tagged {tag}"


def classifier_dir(settings: Settings) -> Path:
    """Where the exported ONNX risk classifier lives."""
    return settings.paths.models_dir / "risk_classifier" / "onnx"


def _check_classifier(settings: Settings) -> tuple[bool, str]:
    folder = classifier_dir(settings)
    missing = [
        n for n in ("model.onnx", "tokenizer.json", "labels.json") if not (folder / n).exists()
    ]
    if missing:
        return False, f"{folder.name} is missing {', '.join(missing)}"
    try:
        from finsight.risks import OnnxClassifier

        OnnxClassifier(folder)
    except Exception as err:  # no onnxruntime, a corrupt file: the reason is what the user needs
        return False, f"it does not load ({type(err).__name__})"
    return True, str(folder.name)


def hf_snapshot(repo: str) -> Path | None:
    """The newest cached snapshot folder of a Hugging Face model, or ``None`` when not cached."""
    hub = os.environ.get("HF_HUB_CACHE") or (
        Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub"
    )
    base = Path(hub) / ("models--" + repo.replace("/", "--")) / "snapshots"
    if not base.is_dir():
        return None
    shots = [p for p in base.iterdir() if (p / "config.json").exists()]
    shots.sort(key=lambda p: p.stat().st_mtime)
    return shots[-1] if shots else None


def _check_embeddings(settings: Settings) -> tuple[bool, str]:
    shot = hf_snapshot(BGE_M3)
    if shot is None:
        return False, f"{BGE_M3} is not downloaded"
    return True, shot.name[:12]


def reranker_file(settings: Settings) -> Path | None:
    """The ONNX reranker weights if present, else ``None`` (the PyTorch copy is in the HF cache)."""
    for name in ("reranker_int8.onnx", "reranker_fp32.onnx"):
        path = settings.paths.models_dir / "reranker_onnx" / name
        if path.exists():
            return path
    return None


def _check_reranker(settings: Settings) -> tuple[bool, str]:
    path = reranker_file(settings)
    if path is not None:
        return True, path.name
    shot = hf_snapshot(BGE_RERANKER)
    if shot is not None:
        return True, shot.name[:12]
    return False, f"{BGE_RERANKER} is not downloaded"


DEFAULT_PROBES: dict[str, Probe] = {
    "ollama": _check_ollama,
    "classifier": _check_classifier,
    "embeddings": _check_embeddings,
    "reranker": _check_reranker,
}


def required_models(settings: Settings) -> tuple[str, ...]:
    """The models this profile's stages use: none when the model stages are switched off."""
    return MODELS if settings.jobs.model_stages else ()


def run_preflight(
    settings: Settings,
    skip: Iterable[str] = (),
    probes: dict[str, Probe] | None = None,
) -> PreflightResult:
    """Check every required model. ``skip`` is the user's "analyse without X"; ``probes`` lets
    tests (and callers that already know) replace a check."""
    chosen = {**DEFAULT_PROBES, **(probes or {})}
    checks = []
    for model in required_models(settings):
        ok, detail = chosen[model](settings)
        checks.append(Check(model, ok, detail))
    return PreflightResult(checks, frozenset(skip))
