"""`configs/splits.yaml`: the frozen split, one entry per IPO (C02 §4, C-ADR-02).

Once ``frozen: true`` is committed, the split changes only by a new C-ADR: ``save_splits``
refuses to overwrite a frozen file unless it is given that ADR id, which is then recorded.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from finsight.splits.assign import IpoRecord, Slice, Source, SplitResult, SplitRules


class SplitEntry(BaseModel):
    """One IPO in the split."""

    ipo_id: str
    company: str
    company_key: str
    source: Source
    slice: Slice
    doc_date: date | None = None
    close_year: int | None = None


class ExcludedEntry(BaseModel):
    """An IPO kept out of every slice, with the reason (reported, never hidden)."""

    ipo_id: str
    reason: str


class SplitsFile(BaseModel):
    """The whole ``splits.yaml``."""

    version: Literal[1] = 1
    frozen: bool = False
    rule: Literal["strict"] = "strict"
    train_cut: date | None = None
    rules: dict[str, float] = Field(default_factory=dict)
    changed_by_adr: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    ipos: list[SplitEntry]
    excluded: list[ExcludedEntry] = Field(default_factory=list)
    demo: list[str] = Field(default_factory=list)  # newest test IPOs (class demo, landing)
    bench: list[str] = Field(default_factory=list)  # set by C4.1 (6 test IPOs, C04 §2)
    bench_dev: list[str] = Field(default_factory=list)  # set by C4.1 (2 dev IPOs)

    @model_validator(mode="after")
    def _subsets(self) -> SplitsFile:
        by = {e.ipo_id: e.slice for e in self.ipos}
        if len(by) != len(self.ipos):
            raise ValueError("an ipo_id appears twice in splits.yaml")
        if set(by) & {x.ipo_id for x in self.excluded}:
            raise ValueError("an excluded IPO also has a slice")
        for name, want in (("demo", "test"), ("bench", "test"), ("bench_dev", "dev")):
            bad = [i for i in getattr(self, name) if by.get(i) != want]
            if bad:
                raise ValueError(f"{name} must be {want} IPOs: {', '.join(bad)}")
        return self

    def by_id(self) -> dict[str, SplitEntry]:
        """Entries keyed by ``ipo_id``."""
        return {e.ipo_id: e for e in self.ipos}

    def ids(self, *slices: str) -> set[str]:
        """IPO ids in any of these slices (``bench`` is part of ``test``)."""
        return {e.ipo_id for e in self.ipos if e.slice in slices}


def to_splits_file(records: list[IpoRecord], result: SplitResult, rules: SplitRules,
                   dropped: dict[str, str] | None = None) -> SplitsFile:  # fmt: skip
    """Build the file content from the assignment (``dropped``: universe rows never assigned)."""
    by = {r.ipo_id: r for r in records}
    entries = [
        SplitEntry(
            ipo_id=i,
            company=by[i].company,
            company_key=by[i].company_key,
            source=by[i].source,
            slice=s,
            doc_date=by[i].doc_date,
            close_year=by[i].close_year,
        )
        for i, s in sorted(result.slices.items())
    ]
    excluded = {**(dropped or {}), **result.excluded}
    counts = Counter(f"{e.slice}/{e.source}" for e in entries)
    return SplitsFile(
        train_cut=result.train_cut,
        rules={
            "dev_share": rules.dev_share,
            "train_share": rules.train_share,
            "demo_newest": rules.demo_newest,
        },
        counts=dict(sorted(counts.items())) | {"excluded": len(excluded)},
        ipos=entries,
        excluded=[ExcludedEntry(ipo_id=i, reason=r) for i, r in sorted(excluded.items())],
        demo=result.demo,
    )


def load_splits(path: Path) -> SplitsFile:
    """Read ``splits.yaml``."""
    return SplitsFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


class FrozenSplitError(RuntimeError):
    """Refused to overwrite a frozen split without a C-ADR."""


def save_splits(splits: SplitsFile, path: Path, adr: str | None = None) -> None:
    """Write ``splits.yaml``; a frozen file is only replaced when ``adr`` names the C-ADR."""
    if path.exists():
        old = load_splits(path)
        if old.frozen:
            if not adr:
                raise FrozenSplitError(
                    f"{path} is frozen; changing it needs a new C-ADR (pass --adr C-ADR-NN)"
                )
            splits.changed_by_adr = [*old.changed_by_adr, adr]
    header = (
        "# Phase 3 time split (C02 §4, C-ADR-02). Written by `python -m finsight.splits build`;\n"
        "# never edit by hand. Once frozen, it changes only by a new C-ADR.\n"
    )
    body = yaml.safe_dump(splits.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
    path.write_text(header + body, encoding="utf-8", newline="\n")


def showcase_mismatches(splits: SplitsFile, roles: dict[str, str]) -> list[str]:
    """Showcase IPOs whose slice differs from ``configs/demo_ipos.yaml`` (empty = consistent)."""
    by = splits.by_id()
    out = []
    for ipo_id, role in sorted(roles.items()):
        got = by[ipo_id].slice if ipo_id in by else "missing"
        if got != role:
            out.append(f"{ipo_id}: demo_ipos.yaml says {role}, splits.yaml says {got}")
    return out
