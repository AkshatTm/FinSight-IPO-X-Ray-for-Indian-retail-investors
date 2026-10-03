"""The demo set: which IPOs we demo and evaluate on (``configs/demo_ipos.yaml``).

Each IPO has two documents, the RHP and the final Prospectus (ADR-023). ``split`` says
whether the IPO is used to tune the system (``dev``) or to report numbers (``test``,
ADR-026). The PDFs themselves live in ``data/raw/`` and are never committed.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from finsight.core.config import project_root


class DocFile(BaseModel):
    doc_id: str  # "doc_" + the first 16 hex characters of sha256 (B-ADR-14)
    file: Path
    pages: int
    sha256: str
    dated: str  # the "Dated" line on the cover page, e.g. "October 29, 2025"


class DemoIpo(BaseModel):
    ipo_id: str
    company: str
    split: Literal["dev", "test"]
    rhp: DocFile
    prospectus: DocFile

    @property
    def primary_doc_id(self) -> str:
        """The showcase report's primary document is the RHP (B02 §3.2)."""
        return self.rhp.doc_id

    @property
    def companion_doc_id(self) -> str:
        """The final Prospectus supplies prices for price-dependent checks."""
        return self.prospectus.doc_id


@lru_cache(maxsize=4)
def _load(path: Path) -> tuple[DemoIpo, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = path.resolve().parent.parent  # configs/ lives at the repo root
    ipos = []
    for entry in raw["ipos"]:
        ipo = DemoIpo.model_validate(entry)
        for doc in (ipo.rhp, ipo.prospectus):
            doc.file = root / doc.file
        ipos.append(ipo)
    return tuple(ipos)


def list_demo_ipos(path: Path | None = None) -> list[DemoIpo]:
    """All demo IPOs, with document paths resolved against the repo root."""
    return list(_load(path or project_root() / "configs" / "demo_ipos.yaml"))


def get_demo_ipo(ipo_id: str, path: Path | None = None) -> DemoIpo:
    for ipo in list_demo_ipos(path):
        if ipo.ipo_id == ipo_id:
            return ipo
    known = ", ".join(i.ipo_id for i in list_demo_ipos(path))
    raise KeyError(f"No demo IPO {ipo_id!r}. Known: {known}")
