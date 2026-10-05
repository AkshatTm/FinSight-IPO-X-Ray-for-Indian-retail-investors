"""The risk bank (B02 §7.1): past IPOs' risk factors with their embeddings.

``bank/risk_bank.parquet`` (built locally, C2.1) has one row per risk of a train or dev IPO:
``company``, ``year``, ``title``, ``embedding`` (bge-m3 on the title + first 2 sentences) and
``ipo_id``, ``doc_date``, ``split``. Test and bench IPOs live in the separate ``risk_eval.parquet``.
Novelty is measured against the IPOs in the rolling reference window (``finsight.splits.
reference_bank``, C-ADR-03), never against the same company's own documents. The old fixed
2018-2023 ``years`` filter is kept for banks without ``ipo_id`` (Phase 2 tests).
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from finsight.core.config import project_root

_SUFFIX = re.compile(r"\b(?:limited|ltd|private|pvt|india|the)\b\.?", re.I)


def company_key(name: str) -> str:
    """Compare companies loosely: "ABC Industries Limited" == "abc industries ltd."."""
    return re.sub(r"[^a-z0-9]+", " ", _SUFFIX.sub(" ", name.lower())).strip()


@dataclass(frozen=True)
class RiskBank:
    """Past IPOs' risk titles with company, year and unit-length embeddings."""

    companies: list[str]
    years: np.ndarray  # (n,) int
    titles: list[str]
    vectors: np.ndarray  # (n, d) float32, unit length
    ipo_ids: list[str] | None = None  # which IPO each row came from (C2.1 banks)

    def __len__(self) -> int:
        return len(self.companies)

    def subset(self, ipo_ids: Collection[str]) -> RiskBank:
        """Only the rows of these IPOs (the rolling reference window); needs ``ipo_ids``."""
        if self.ipo_ids is None:
            raise ValueError(
                "this bank has no ipo_id column; build it with scripts/build_risk_bank.py"
            )
        wanted = set(ipo_ids)
        idx = np.array([i for i, x in enumerate(self.ipo_ids) if x in wanted], dtype=np.int64)
        return RiskBank(
            companies=[self.companies[i] for i in idx],
            years=self.years[idx],
            titles=[self.titles[i] for i in idx],
            vectors=self.vectors[idx],
            ipo_ids=[self.ipo_ids[i] for i in idx],
        )

    def concat(self, other: RiskBank) -> RiskBank:
        """This bank followed by ``other`` (train+dev bank + the eval bank = the product bank)."""
        if self.ipo_ids is None or other.ipo_ids is None:
            raise ValueError("both banks need an ipo_id column")
        return RiskBank(
            companies=[*self.companies, *other.companies],
            years=np.concatenate([self.years, other.years]),
            titles=[*self.titles, *other.titles],
            vectors=np.vstack([self.vectors, other.vectors]),
            ipo_ids=[*self.ipo_ids, *other.ipo_ids],
        )

    def keys(self) -> list[str]:
        """The normalised company key of every row (to exclude the issuer itself)."""
        return [company_key(c) for c in self.companies]


def normalise(vectors: np.ndarray) -> np.ndarray:
    """Scale each row to unit length (zero rows stay zero)."""
    v = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    return v / np.where(norms == 0, 1.0, norms)


def load_bank(path: Path, years: tuple[int, int] | None = (2018, 2023)) -> RiskBank:
    """Read a parquet bank; ``years`` keeps those years inclusive (``None`` keeps every row).

    Banks built by ``scripts/build_risk_bank.py`` have an ``ipo_id`` column and are normally read
    with ``years=None`` and cut to the reference window with ``finsight.splits.reference_bank``.
    """
    import pyarrow.parquet as pq

    names = set(pq.read_schema(path).names)
    cols = ["company", "year", "title", "embedding"] + (["ipo_id"] if "ipo_id" in names else [])
    table = pq.read_table(path, columns=cols)
    year = np.asarray(table.column("year").to_numpy(), dtype=np.int64)
    keep = (
        np.ones(len(year), dtype=bool) if years is None else (year >= years[0]) & (year <= years[1])
    )
    idx = np.flatnonzero(keep)
    emb = np.stack([np.asarray(e, dtype=np.float32) for e in table.column("embedding").to_pylist()])
    companies = table.column("company").to_pylist()
    titles = table.column("title").to_pylist()
    ids = table.column("ipo_id").to_pylist() if "ipo_id" in names else None
    return RiskBank(
        companies=[str(companies[i]) for i in idx],
        years=year[idx],
        titles=[str(titles[i]) for i in idx],
        vectors=normalise(emb[idx]),
        ipo_ids=[str(ids[i]) for i in idx] if ids is not None else None,
    )


@lru_cache(maxsize=1)
def risks_config(path: Path | None = None) -> dict[str, Any]:
    """The risk settings (``configs/risks.yaml``)."""
    cfg: dict[str, Any] = yaml.safe_load(
        (path or project_root() / "configs" / "risks.yaml").read_text(encoding="utf-8")
    )
    return cfg
