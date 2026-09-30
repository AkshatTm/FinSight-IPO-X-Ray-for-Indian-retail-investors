"""The sections stage: parsed JSON -> sections JSON, plus the demo-set section matrix."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from finsight.core.schemas import DocType, Section
from finsight.parse import KEY_SECTIONS, find_sections
from finsight.pipeline.layout import doc_outputs
from finsight.pipeline.parse_stage import load_parsed

_SECTIONS = TypeAdapter(list[Section])


def run_sections(processed_dir: Path, ipo_id: str, doc: DocType) -> list[Section]:
    sections = find_sections(load_parsed(processed_dir, ipo_id, doc))
    out = doc_outputs(processed_dir, ipo_id, doc).sections
    out.write_bytes(_SECTIONS.dump_json(sections, indent=1))
    return sections


def load_sections(processed_dir: Path, ipo_id: str, doc: DocType) -> list[Section]:
    path = doc_outputs(processed_dir, ipo_id, doc).sections
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run `pipeline build --stage sections` first")
    return _SECTIONS.validate_json(path.read_bytes())


def section_matrix(results: dict[tuple[str, DocType], list[Section]]) -> dict[str, object]:
    """Found / not-found per key section and document, with the G1 count (eval_results)."""
    rows: dict[str, dict[str, object]] = {}
    found_in_all: dict[DocType, int] = {"rhp": 0, "prospectus": 0}
    for (ipo_id, doc), sections in sorted(results.items()):
        by_id = {s.id: s for s in sections}
        cells = {
            key: (
                {
                    "start_page": by_id[key].start_page,
                    "end_page": by_id[key].end_page,
                    "method": by_id[key].method,
                    "confidence": by_id[key].confidence,
                }
                if key in by_id
                else None
            )
            for key in KEY_SECTIONS
        }
        rows[f"{ipo_id}:{doc}"] = {"n_sections": len(sections), "key": cells}
        found_in_all[doc] += all(cells.values())
    n_docs: dict[DocType, int] = {"rhp": 0, "prospectus": 0}
    for _, doc in results:
        n_docs[doc] += 1
    return {
        "key_sections": list(KEY_SECTIONS),
        "all_key_found": {doc: f"{found_in_all[doc]}/{n_docs[doc]}" for doc in n_docs},
        "documents": rows,
    }


def write_matrix(path: Path, matrix: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matrix, indent=1) + "\n", encoding="utf-8", newline="\n")
