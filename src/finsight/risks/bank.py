"""The risk bank (B02 §7.1): past IPOs' risk factors with their embeddings.

``bank/risk_bank.parquet`` (built locally in B2.1b) has one row per corpus risk: ``company``,
``year``, ``title`` and ``embedding`` (bge-m3 on the title + first 2 sentences). Novelty is
measured against the 2018-2023 rows only, and never against the same company's own documents.
"""

from __future__ import annotations

import re
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
    companies: list[str]
    years: np.ndarray  # (n,) int
    titles: list[str]
    vectors: np.ndarray  # (n, d) float32, unit length

    def __len__(self) -> int:
        return len(self.companies)

    def keys(self) -> list[str]:
        return [company_key(c) for c in self.companies]


def normalise(vectors: np.ndarray) -> np.ndarray:
    v = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    return v / np.where(norms == 0, 1.0, norms)


def load_bank(path: Path, years: tuple[int, int] = (2018, 2023)) -> RiskBank:
    """Read the parquet bank and keep the reference years (inclusive)."""
    import pyarrow.parquet as pq

    table = pq.read_table(path, columns=["company", "year", "title", "embedding"])
    year = np.asarray(table.column("year").to_numpy(), dtype=np.int64)
    keep = (year >= years[0]) & (year <= years[1])
    idx = np.flatnonzero(keep)
    emb = np.stack([np.asarray(e, dtype=np.float32) for e in table.column("embedding").to_pylist()])
    companies = table.column("company").to_pylist()
    titles = table.column("title").to_pylist()
    return RiskBank(
        companies=[str(companies[i]) for i in idx],
        years=year[idx],
        titles=[str(titles[i]) for i in idx],
        vectors=normalise(emb[idx]),
    )


@lru_cache(maxsize=1)
def risks_config(path: Path | None = None) -> dict[str, Any]:
    cfg: dict[str, Any] = yaml.safe_load(
        (path or project_root() / "configs" / "risks.yaml").read_text(encoding="utf-8")
    )
    return cfg
