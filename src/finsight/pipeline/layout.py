"""Where the offline pipeline writes things (02_ARCHITECTURE.md section 9)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from finsight.core.schemas import DocType


@dataclass(frozen=True)
class DocOutputs:
    parsed: Path  # parsed.json (RHP) or parsed_prospectus.json
    pages_dir: Path  # pages/ (RHP) or pages_prospectus/


def doc_outputs(processed_dir: Path, ipo_id: str, doc: DocType) -> DocOutputs:
    base = processed_dir / ipo_id
    if doc == "rhp":
        return DocOutputs(parsed=base / "parsed.json", pages_dir=base / "pages")
    return DocOutputs(parsed=base / "parsed_prospectus.json", pages_dir=base / "pages_prospectus")
