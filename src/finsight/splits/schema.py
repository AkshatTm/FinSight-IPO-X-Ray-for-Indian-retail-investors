"""The `configs/ipo_universe.csv` contract (C02 §2): one row per mainboard IPO, metadata only.

C1.1 writes the file, C1.2 fills ``sha256`` and ``status``, C1.3 fills ``pages`` and sets
``parsed``/``failed``. The split itself is **not** a column: it lives in ``configs/splits.yaml``
(one source of truth, C-ADR-02).
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

UNIVERSE_COLUMNS = (
    "ipo_id", "company", "exchange", "doc_type", "doc_date", "listing_date",
    "source_url", "sha256", "pages", "status", "reason",
)  # fmt: skip

Status = Literal["listed", "downloaded", "parsed", "failed", "excluded"]
FINAL_STATUSES: frozenset[str] = frozenset({"parsed", "failed", "excluded"})


class UniverseError(ValueError):
    """The universe file breaks the C02 §2 contract (the message names the row and column)."""


class UniverseRow(BaseModel):
    """One IPO offer document in the universe."""

    ipo_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*-\d{4}$")  # corpus `ipo_slug` shape
    company: str = Field(min_length=2)
    exchange: Literal["NSE", "BSE", "both"]
    doc_type: Literal["rhp", "prospectus"]
    doc_date: date  # the "Dated" line on the cover
    listing_date: date | None = None
    source_url: str = Field(min_length=1)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    pages: int | None = Field(default=None, gt=0)
    status: Status
    reason: str | None = None

    @field_validator("listing_date", "sha256", "pages", "reason", mode="before")
    @classmethod
    def _blank_is_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v

    @model_validator(mode="after")
    def _reason_when_dropped(self) -> UniverseRow:
        if self.status in ("failed", "excluded") and not self.reason:
            raise ValueError("reason is required when status is failed or excluded")
        return self


def load_universe(path: Path) -> list[UniverseRow]:
    """Read and validate the universe CSV; raise ``UniverseError`` naming the first problem."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != UNIVERSE_COLUMNS:
            raise UniverseError(f"{path.name}: columns must be {', '.join(UNIVERSE_COLUMNS)}")
        rows: list[UniverseRow] = []
        seen: set[str] = set()
        for line, raw in enumerate(reader, start=2):
            try:
                row = UniverseRow.model_validate(raw)
            except ValidationError as err:
                first = err.errors()[0]
                where = ".".join(str(p) for p in first["loc"]) or "row"
                raise UniverseError(f"{path.name} line {line}: {where}: {first['msg']}") from err
            if row.ipo_id in seen:
                raise UniverseError(f"{path.name} line {line}: duplicate ipo_id {row.ipo_id}")
            seen.add(row.ipo_id)
            rows.append(row)
    return rows
