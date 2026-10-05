"""Rolling reference window (C02 §5, C-ADR-03): "past IPOs" = dated before the document,
within the last ``window_years`` (``configs/reference.yaml``).

- New and showcase documents count by ``doc_date``: ``as_of - years <= doc_date < as_of``.
- Corpus IPOs have only a close year: they count when
  ``as_of.year - years <= close_year <= as_of.year - 1`` (never in the as-of year itself).
- ``kind="eval"``: train + dev only, every test/bench IPO left out (computed per test IPO;
  never stored in configs).
- ``kind="product"``: every collected IPO (train, dev, test) except the upload itself.
- Excluded IPOs are never in either window. The issuer is left out by ``ipo_id`` and by
  company key.
"""

from __future__ import annotations

import statistics
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml

from finsight.core.config import project_root
from finsight.risks import RiskBank, company_key
from finsight.splits.store import SplitEntry, SplitsFile

RefKind = Literal["eval", "product"]
_SLICES: dict[str, frozenset[str]] = {
    "eval": frozenset({"train", "dev"}),
    "product": frozenset({"train", "dev", "test"}),
}


@lru_cache(maxsize=4)
def reference_config(path: Path | None = None) -> dict[str, Any]:
    """``configs/reference.yaml``."""
    cfg: dict[str, Any] = yaml.safe_load(
        (path or project_root() / "configs" / "reference.yaml").read_text(encoding="utf-8")
    )
    return cfg


def years_before(day: date, years: int) -> date:
    """The same calendar day ``years`` earlier (29 Feb falls back to 28 Feb)."""
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def in_window(entry: SplitEntry, as_of: date, years: int) -> bool:
    """Whether this IPO is "past" and recent enough as of ``as_of``."""
    if entry.doc_date is not None:
        return years_before(as_of, years) <= entry.doc_date < as_of
    if entry.close_year is not None:
        return as_of.year - years <= entry.close_year <= as_of.year - 1
    return False


def ipos_before(
    splits: SplitsFile,
    as_of: date,
    years: int | None = None,
    *,
    kind: RefKind = "eval",
    exclude_ipo: str | None = None,
    exclude_company: str | None = None,
) -> list[SplitEntry]:
    """The reference IPOs for a document dated ``as_of`` (sorted by date, then id)."""
    years = int(reference_config()["window_years"]) if years is None else years
    allowed = _SLICES[kind]
    skip_key = company_key(exclude_company) if exclude_company else None
    if exclude_ipo is not None:
        own = splits.by_id().get(exclude_ipo)
        if own is not None:
            skip_key = skip_key or own.company_key
    out = [
        e for e in splits.ipos
        if e.slice in allowed and e.ipo_id != exclude_ipo
        and (skip_key is None or e.company_key != skip_key)
        and in_window(e, as_of, years)
    ]  # fmt: skip
    return sorted(out, key=lambda e: (e.doc_date or date(e.close_year or 1, 12, 31), e.ipo_id))


def window_n(splits: SplitsFile, years: int | None = None) -> dict[str, int]:
    """Eval window size per test IPO (reported with every percentile, C02 §5)."""
    return {
        e.ipo_id: len(ipos_before(splits, e.doc_date, years, kind="eval", exclude_ipo=e.ipo_id))
        for e in splits.ipos
        if e.slice == "test" and e.doc_date is not None
    }


def window_summary(sizes: dict[str, int]) -> str:
    """``n = min / median / max`` over the test IPOs, for the CLI and the datasheet."""
    if not sizes:
        return "no dated test IPOs"
    v = sorted(sizes.values())
    return f"eval window n per test IPO: min {v[0]}, median {statistics.median(v):g}, max {v[-1]}"


def reference_bank(
    bank: RiskBank,
    splits: SplitsFile,
    as_of: date,
    years: int | None = None,
    *,
    kind: RefKind = "eval",
    exclude_ipo: str | None = None,
    exclude_company: str | None = None,
) -> RiskBank:
    """The risk bank cut to the reference window of a document dated ``as_of`` (C-ADR-03).

    This is how novelty is wired to the rolling window: ``kind="eval"`` leaves every test and
    bench IPO out; ``kind="product"`` keeps all collected IPOs. The issuer is left out by id and
    by company key.
    """
    ids = {
        e.ipo_id
        for e in ipos_before(
            splits,
            as_of,
            years,
            kind=kind,
            exclude_ipo=exclude_ipo,
            exclude_company=exclude_company,
        )
    }
    return bank.subset(ids)
