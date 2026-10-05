"""Build the split from the universe, the corpus and the showcase list (C1.4).

Without ``freeze`` it only prints the counts (Akshat confirms them first, C02 §4). With
``freeze`` it also writes ``configs/splits.yaml`` (``frozen: true``) and the retro manifests,
then runs the leakage check over every manifest in ``data/manifests/``.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from finsight.ingest import list_demo_ipos
from finsight.splits.assign import IpoRecord, SplitRules, assign, check_strict
from finsight.splits.leakage import check_manifests
from finsight.splits.manifest import read_manifests, write_manifest
from finsight.splits.reference import window_n, window_summary
from finsight.splits.retro import retro_manifests
from finsight.splits.schema import load_universe
from finsight.splits.store import SplitsFile, save_splits, showcase_mismatches, to_splits_file

PENDING = ("listed", "downloaded")


class BuildError(RuntimeError):
    """The split cannot be built or frozen (the message says what to do first)."""


@dataclass
class BuildPaths:
    """Inputs and outputs of the build (all relative to the repo root by default)."""

    universe: Path
    corpus_dir: Path
    demo: Path
    out: Path
    manifests: Path
    processed: Path
    root: Path


@dataclass
class BuildOutcome:
    """What the build did, for the CLI and tests."""

    splits: SplitsFile
    report: list[str] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)


def cover_date(text: str) -> date:
    """``"April 22, 2025"`` -> ``date(2025, 4, 22)`` (the showcase "Dated" line)."""
    return datetime.strptime(text.strip(), "%B %d, %Y").date()


def corpus_records(corpus_dir: Path) -> list[IpoRecord]:
    """One record per corpus JSON (id, company, close year; the page text is not used)."""
    out = []
    for path in sorted(corpus_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        out.append(IpoRecord.corpus(raw["ipo_id"], raw["company"], raw.get("close_year")))
    return out


def gather(paths: BuildPaths) -> tuple[list[IpoRecord], dict[str, str], list[str], dict[str, str]]:
    """Records to split, universe rows dropped (id -> reason), pending ids, showcase roles."""
    if not paths.universe.is_file():
        raise BuildError(f"{paths.universe} not found: run C1.1 (universe) first")
    showcase = list_demo_ipos(paths.demo)
    roles: dict[str, str] = {s.ipo_id: s.split for s in showcase}
    records = [
        IpoRecord.showcase(s.ipo_id, s.company, cover_date(s.rhp.dated), s.split) for s in showcase
    ]
    dropped: dict[str, str] = {}
    pending: list[str] = []
    for row in load_universe(paths.universe):
        if row.ipo_id in roles:
            continue  # showcase roles and dates come from demo_ipos.yaml
        if row.status == "parsed":
            records.append(IpoRecord.new(row.ipo_id, row.company, row.doc_date))
        elif row.status in PENDING:
            pending.append(row.ipo_id)
        else:
            dropped[row.ipo_id] = f"{row.status}: {row.reason}"
    records += corpus_records(paths.corpus_dir)
    return records, dropped, pending, roles


def _report(splits: SplitsFile, pending: list[str]) -> list[str]:
    lines = [f"train cut (earliest test document): {splits.train_cut}"]
    lines.append("slice/source counts: " + ", ".join(f"{k} {v}" for k, v in splits.counts.items()))
    years: Counter[tuple[int, str]] = Counter()
    for e in splits.ipos:
        year = e.doc_date.year if e.doc_date else e.close_year
        if year is not None:
            years[(year, e.slice)] += 1
    for year in sorted({y for y, _ in years}):
        row = ", ".join(
            f"{s} {years[(year, s)]}" for s in ("train", "dev", "test") if years[(year, s)]
        )
        lines.append(f"  {year}: {row}")
    reasons = Counter(x.reason.split(":")[0].split(" IPO ")[0] for x in splits.excluded)
    if reasons:
        lines.append("excluded: " + ", ".join(f"{r} {n}" for r, n in reasons.most_common()))
    if pending:
        lines.append(f"not final yet (listed/downloaded): {len(pending)}; finish C1.2/C1.3 first")
    lines.append(window_summary(window_n(splits)))
    lines.append("demo (newest test IPOs): " + (", ".join(splits.demo) or "none"))
    return lines


def build(paths: BuildPaths, rules: SplitRules, freeze: bool = False,
          adr: str | None = None) -> BuildOutcome:  # fmt: skip
    """Assign, check and report; with ``freeze``, write splits.yaml + manifests and check them."""
    records, dropped, pending, roles = gather(paths)
    result = assign(records, rules)
    check_strict(result, records)
    splits = to_splits_file(records, result, rules, dropped)
    mismatch = showcase_mismatches(splits, roles)
    if mismatch:
        raise BuildError("showcase roles differ from demo_ipos.yaml: " + "; ".join(mismatch))
    outcome = BuildOutcome(splits, _report(splits, pending))
    if not freeze:
        outcome.report.append("dry run: nothing written (add --freeze after Akshat confirms)")
        return outcome
    if pending:
        raise BuildError(f"{len(pending)} universe rows are not final (listed/downloaded)")
    splits.frozen = True
    save_splits(splits, paths.out, adr)
    outcome.written.append(paths.out)
    made, missing = retro_manifests(paths.processed, paths.root)
    outcome.written += [write_manifest(m, paths.manifests) for m in made]
    outcome.report += missing
    leaks = check_manifests(read_manifests(paths.manifests), splits)
    if leaks:
        raise BuildError("leakage: " + "; ".join(str(v) for v in leaks[:10]))
    outcome.report.append(f"frozen: {paths.out}; {len(made)} manifests; leakage check clean")
    return outcome
