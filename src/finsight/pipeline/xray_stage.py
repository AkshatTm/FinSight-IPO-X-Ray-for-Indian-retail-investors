"""The qa and xray stages: QA candidates, then the X-Ray JSON of one IPO.

``qa`` needs the opt-in ``ml`` dependency group and the GPU
(``uv run --group ml --group tables python -m finsight.pipeline build --stage qa``); ``xray`` is
plain Python and uses whatever candidates exist (rules always, QA when present).
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from finsight.core.schemas import Candidate, DocType, XRay
from finsight.extract import DocInputs, QAExtractor, build_xray, load_fields, objects_pure_ofs
from finsight.ingest.registry import DemoIpo
from finsight.parse import KEY_SECTIONS
from finsight.pipeline.layout import doc_outputs, xray_path
from finsight.pipeline.parse_stage import load_parsed
from finsight.pipeline.rules_stage import RulesRun, load_candidates
from finsight.pipeline.sections_stage import load_sections

_CANDIDATES = TypeAdapter(RulesRun)
DOCS: tuple[DocType, ...] = ("rhp", "prospectus")


def run_qa(
    processed_dir: Path,
    ipo_id: str,
    doc: DocType,
    extractors: Sequence[QAExtractor] | None = None,
) -> RulesRun:
    """QA candidates for every field that names one of the extractors (``extractor`` or
    ``fallback`` in fields.yaml); writes ``candidates_qa*.json``."""
    parsed = load_parsed(processed_dir, ipo_id, doc)
    sections = load_sections(processed_dir, ipo_id, doc)
    qa = list(extractors) if extractors else [QAExtractor()]
    found = {
        f.id: [c for e in qa for c in e.extract(parsed, sections, [], f)] for f in load_fields()
    }
    doc_outputs(processed_dir, ipo_id, doc).candidates_qa.write_bytes(
        _CANDIDATES.dump_json(found, indent=1)
    )
    return found


def _load_qa(processed_dir: Path, ipo_id: str, doc: DocType) -> RulesRun:
    path = doc_outputs(processed_dir, ipo_id, doc).candidates_qa
    return _CANDIDATES.validate_json(path.read_bytes()) if path.exists() else {}


def _inputs(processed_dir: Path, ipo_id: str, doc: DocType) -> DocInputs:
    parsed = load_parsed(processed_dir, ipo_id, doc)
    sections = load_sections(processed_dir, ipo_id, doc)
    rules, qa = load_candidates(processed_dir, ipo_id, doc), _load_qa(processed_dir, ipo_id, doc)
    merged: dict[str, list[Candidate]] = {
        f.id: rules.get(f.id, []) + qa.get(f.id, []) for f in load_fields()
    }
    found = {s.id for s in sections}
    return DocInputs(
        candidates=merged,
        pure_ofs=objects_pure_ofs(parsed, sections),
        missing_sections=[s for s in KEY_SECTIONS if s != "cover" and s not in found],
    )


def run_xray(processed_dir: Path, ipo: DemoIpo, now: datetime | None = None) -> XRay:
    docs = {doc: _inputs(processed_dir, ipo.ipo_id, doc) for doc in DOCS}
    xray = build_xray(ipo.ipo_id, ipo.company, docs, now or datetime.now(UTC))
    xray_path(processed_dir, ipo.ipo_id).write_text(
        xray.model_dump_json(indent=1), encoding="utf-8"
    )
    return xray


def load_xray(processed_dir: Path, ipo_id: str) -> XRay:
    path = xray_path(processed_dir, ipo_id)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run `pipeline build --stage xray` first")
    return XRay.model_validate_json(path.read_text(encoding="utf-8"))


def xray_summary(xrays: list[XRay]) -> dict[str, object]:
    """Coverage only (no gold scores): verdicts, reasons and consistency checks per IPO."""
    per_field: dict[str, Counter[str]] = {}
    checks: dict[str, dict[str, str]] = {}
    for xray in xrays:
        for f in xray.fields:
            counter = per_field.setdefault(f.field_id, Counter())
            counter[f"verdict:{f.verdict}"] += 1
            counter[f"reason:{f.reason_code}"] += 1
            counter["has_value"] += f.chosen is not None
        totals = next(f for f in xray.fields if f.field_id == "total_issue_size")
        checks[xray.ipo_id] = {c.check: f"{c.status}/{c.reason_code}" for c in totals.checks}
    return {
        "n_ipos": len(xrays),
        "fields": {k: dict(sorted(v.items())) for k, v in per_field.items()},
        "consistency": checks,
    }


def write_xray_summary(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
