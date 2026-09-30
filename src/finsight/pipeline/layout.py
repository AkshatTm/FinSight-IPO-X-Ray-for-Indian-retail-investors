"""Where the offline pipeline writes things (02_ARCHITECTURE.md section 9)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from finsight.core.schemas import DocType


@dataclass(frozen=True)
class DocOutputs:
    parsed: Path  # parsed.json (RHP) or parsed_prospectus.json
    pages_dir: Path  # pages/ (RHP) or pages_prospectus/
    sections: Path  # sections.json (RHP) or sections_prospectus.json
    tables: Path  # tables.json (RHP) or tables_prospectus.json
    candidates: Path  # candidates_rules.json (RHP) or candidates_rules_prospectus.json


def doc_outputs(processed_dir: Path, ipo_id: str, doc: DocType) -> DocOutputs:
    base = processed_dir / ipo_id
    suffix = "" if doc == "rhp" else "_prospectus"
    return DocOutputs(
        parsed=base / f"parsed{suffix}.json",
        pages_dir=base / f"pages{suffix}",
        sections=base / f"sections{suffix}.json",
        tables=base / f"tables{suffix}.json",
        candidates=base / f"candidates_rules{suffix}.json",
    )
