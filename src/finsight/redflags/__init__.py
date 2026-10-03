"""Red flags: 13 rule-based checks on the numbers an offer document discloses (B01 §5).

``evaluate(inputs)`` always returns all 13 checks, each OK / Watch / Concern / Not available /
Not applicable with one plain sentence (B05 §5.4), the numbers it used and the pages behind them.
Inputs come from ``summary.json`` and the X-Ray (``inputs_from_summary``, the pipeline) or from
the gold v3 rows (``inputs_from_gold``, the status gold), so both are judged by the same rules.
Thresholds live in ``configs/redflags.yaml`` and their ``version`` is stored with every result.
The checks describe the document; they never say what to do about it (B-ADR-13).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from finsight.core.config import project_root
from finsight.core.schemas import FinancialSummary, RedFlag, RedFlags, XRay
from finsight.redflags.inputs import (
    RedFlagInputs,
    auditor_kind,
    inputs_from_gold,
    inputs_from_summary,
)
from finsight.redflags.rules import CHECKS, DRAFT_SENTENCES, Result
from finsight.storage import Storage, doc_key, get_json, put_json

POINTS = {"concern": 2, "watch": 1}
REDFLAGS_FILE = "redflags.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """The checks' titles, rule texts and thresholds (``configs/redflags.yaml``)."""
    cfg: dict[str, Any] = yaml.safe_load(
        (path or project_root() / "configs" / "redflags.yaml").read_text(encoding="utf-8")
    )
    return cfg


def evaluate(inputs: RedFlagInputs, cfg: dict[str, Any] | None = None) -> RedFlags:
    """Run all 13 checks on one document's inputs."""
    c = cfg or load_config()
    flags: list[RedFlag] = []
    for rf_id, check in CHECKS.items():
        spec = c["checks"][rf_id]
        result: Result = check(inputs, spec, str(c["default_missing"]))
        flags.append(
            RedFlag(
                id=rf_id,
                title=str(spec["title"]),
                status=result.status,
                sentence=result.sentence,
                numbers_used=result.numbers,
                evidence=[inputs.evidence[k] for k in result.evidence_keys if k in inputs.evidence],
                rule=str(spec["rule"]),
                points=POINTS.get(result.status, 0),
            )
        )
    return RedFlags(
        flags=flags,
        financial_company=inputs.is_financial_company,
        thresholds_version=str(c["version"]),
    )


def build(storage: Storage, doc_id: str) -> RedFlags:
    """The ``redflags`` stage: read ``summary.json`` (and ``xray.json`` if present), write
    ``redflags.json``. Wired into the upload stages when the ``financials`` stage lands (B1.3)."""
    summary = FinancialSummary.model_validate(get_json(storage, doc_key(doc_id, "summary.json")))
    xray_key = doc_key(doc_id, "xray.json")
    xray = XRay.model_validate(get_json(storage, xray_key)) if storage.exists(xray_key) else None
    flags = evaluate(inputs_from_summary(summary, xray))
    put_json(storage, doc_key(doc_id, REDFLAGS_FILE), flags.model_dump(mode="json"))
    return flags


__all__ = [
    "CHECKS",
    "DRAFT_SENTENCES",
    "POINTS",
    "REDFLAGS_FILE",
    "RedFlagInputs",
    "auditor_kind",
    "build",
    "evaluate",
    "inputs_from_gold",
    "inputs_from_summary",
    "load_config",
]
