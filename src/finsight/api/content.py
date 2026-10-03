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
