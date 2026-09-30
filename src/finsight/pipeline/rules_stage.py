"""The rules stage: parsed + sections + tables -> rule/table candidates for every field."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from finsight.core.schemas import Candidate, DocType
from finsight.extract import RulesExtractor, TableExtractor, load_fields
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.parse_stage import load_parsed
from finsight.pipeline.sections_stage import load_sections
from finsight.pipeline.tables_stage import load_tables

RulesRun = dict[str, list[Candidate]]
_CANDIDATES = TypeAdapter(RulesRun)


def run_rules(processed_dir: Path, ipo_id: str, doc: DocType) -> RulesRun:
    """Run the rules (and the Objects table reader) for one document; write its candidates."""
    parsed = load_parsed(processed_dir, ipo_id, doc)
    sections = load_sections(processed_dir, ipo_id, doc)
    tables_path = doc_outputs(processed_dir, ipo_id, doc).tables
    tables = load_tables(processed_dir, ipo_id, doc) if tables_path.exists() else []
    extractors = {"rules": RulesExtractor(), "table": TableExtractor()}
    found: RulesRun = {}
    for field in load_fields():
        extractor = extractors.get(field.extractor)
        found[field.id] = extractor.extract(parsed, sections, tables, field) if extractor else []
    doc_outputs(processed_dir, ipo_id, doc).candidates.write_bytes(
        _CANDIDATES.dump_json(found, indent=1)
    )
    return found


def load_candidates(processed_dir: Path, ipo_id: str, doc: DocType) -> RulesRun:
    path = doc_outputs(processed_dir, ipo_id, doc).candidates
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run `pipeline build --stage rules` first")
    return _CANDIDATES.validate_json(path.read_bytes())


def rules_summary(results: dict[tuple[str, DocType], RulesRun]) -> dict[str, object]:
    """Coverage only: how many fields got a candidate, and the page of the best one."""
    docs: dict[str, object] = {}
    coverage: dict[str, dict[str, int]] = {"rhp": {}, "prospectus": {}}
    for (ipo_id, doc), found in sorted(results.items()):
        docs[f"{ipo_id}:{doc}"] = {
            field_id: (
                {"n": len(cands), "page": cands[0].page, "kind": cands[0].value.kind}
                if cands and cands[0].value
                else None
            )
            for field_id, cands in found.items()
        }
        for field_id, cands in found.items():
            coverage[doc][field_id] = coverage[doc].get(field_id, 0) + bool(cands)
    return {"documents_with_a_candidate_per_field": coverage, "documents": docs}


def write_rules_summary(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=1, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
