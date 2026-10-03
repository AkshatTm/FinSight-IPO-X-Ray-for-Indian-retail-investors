"""Glossary and Model Lab payloads (both read from committed config or ``eval_results/``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from finsight.api.errors import ApiError
from finsight.api.models import GlossaryEntry
from finsight.core.config import project_root
from finsight.core.schemas import Language

# 06 lab endpoint -> the result file that backs it. Missing files answer 404, and the frontend
# hides that Lab section (spec 8: "if /api/lab/frontier has data").
LAB_FILES = {
    "ladder": "ladder_table.json",
    "fields": "xray_accuracy.json",
    "verifier": "verifier.json",
    "weaklabels": "weaklabel_stats.json",
    "frontier": "frontier.json",
    "retrieval": "retrieval.json",
    "asr": "asr.json",
}
# Extra files merged into a payload under a key (06: weaklabels = stats + audit precision).
LAB_EXTRAS = {"weaklabels": {"audit": "weaklabel_audit.json"}}

# Phase 2 Lab (B06 §5): ``/api/lab/b/{name}`` -> files in ``eval_results/b/``. A dict of files
# means several files merged into one payload; ``classifier`` merges every ``classifier_*.json``.
LAB_B_FILES: dict[str, str | dict[str, str]] = {
    "segmentation": "segmentation.json",
    "summary": "summary_extraction.json",
    "redflags": "redflags.json",
    "classifier": "classifier_*.json",
    "seriousness": "seriousness.json",
    "simplify": {"human": "simplify_human.json", "checks": "simplify_checks.json"},
    "readability": "readability.json",
    "novelty": "novelty.json",
    "risklevel": "risklevel_validation.json",
    "latency": "latency_cloud.json",
    "cost": "cost.json",
}


def glossary(lang: Language) -> list[GlossaryEntry]:
    """Glossary terms from ``configs/glossary.yaml``, falling back to English."""
    rows = yaml.safe_load((project_root() / "configs" / "glossary.yaml").read_text("utf-8"))[
        "terms"
    ]
    return [
        GlossaryEntry(
            term=r["id"],
            title=r["title"][lang] or r["title"]["en"],
            body=r["body"][lang] or r["body"]["en"],
        )
        for r in rows
    ]


def lab(eval_dir: Path, name: str) -> dict[str, Any]:
    """Read one Model Lab result file (404 ``not_available`` if it was not run)."""
    path = eval_dir / LAB_FILES[name]
    if not path.exists():
        raise ApiError(
            404, "not_available", f"No results for '{name}' yet.",
            hint="The experiment has not been run on this machine.",
        )  # fmt: skip
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    for key, extra in LAB_EXTRAS.get(name, {}).items():
        if (eval_dir / extra).exists():
            payload[key] = json.loads((eval_dir / extra).read_text(encoding="utf-8"))
    return payload


def _not_run(name: str) -> ApiError:
    return ApiError(
        404, "not_available", f"No results for '{name}' yet.",
        hint="The experiment has not been run on this machine.",
    )  # fmt: skip


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def lab_b(eval_dir: Path, name: str) -> dict[str, Any]:
    """Read one Phase 2 Model Lab result (B06 §5); 404 ``not_available`` when nothing was run.

    ``classifier`` answers ``{"systems": [...]}``, one entry per ``classifier_*.json`` with its
    ``file`` stem; ``simplify`` answers ``{"human": ..., "checks": ...}`` with whichever exist.
    """
    root = eval_dir / "b"
    spec = LAB_B_FILES[name]
    if isinstance(spec, dict):
        parts = {key: _read(root / f) for key, f in spec.items() if (root / f).exists()}
        if not parts:
            raise _not_run(name)
        return parts
    if "*" in spec:
        files = sorted(root.glob(spec)) if root.is_dir() else []
        if not files:
            raise _not_run(name)
        return {"systems": [{"file": f.stem, **_read(f)} for f in files]}
    path = root / spec
    if not path.exists():
        raise _not_run(name)
    payload: dict[str, Any] = _read(path)
    return payload
