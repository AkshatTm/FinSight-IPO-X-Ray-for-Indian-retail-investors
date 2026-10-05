"""Leakage guard (C02 §4, C-ADR-02): no test/bench IPO in anything that trains or tunes.

A manifest of kind ``train``, ``fit`` or ``eval_reference`` fails when it lists:

- a ``test`` IPO (``bench`` is part of ``test``), matched by ``ipo_id``;
- any IPO whose company key equals a test IPO's (re-filers, renamed companies);
- an excluded IPO, or an id that ``splits.yaml`` does not know;
- for ``train`` and ``fit``: a ``product_reference`` artefact among its ``inputs``.

``eval`` and ``product_reference`` manifests may hold test IPOs.
"""

from __future__ import annotations

from dataclasses import dataclass

from finsight.splits.manifest import NO_TEST_KINDS, Manifest
from finsight.splits.store import SplitsFile


@dataclass(frozen=True)
class Violation:
    """One leak: which artefact, which IPO (or input) and why."""

    artefact: str
    item: str
    reason: str

    def __str__(self) -> str:
        return f"{self.artefact}: {self.item}: {self.reason}"


def check_manifests(manifests: list[Manifest], splits: SplitsFile) -> list[Violation]:
    """All leaks in these manifests under this split (empty list = clean)."""
    by_id = splits.by_id()
    excluded = {x.ipo_id for x in splits.excluded}
    test_keys = {e.company_key: e.ipo_id for e in splits.ipos if e.slice == "test"}
    kinds = {m.artefact: m.kind for m in manifests}
    out: list[Violation] = []
    for m in manifests:
        if m.kind not in NO_TEST_KINDS:
            continue
        for ipo in sorted(set(m.ipo_ids)):
            entry = by_id.get(ipo)
            if ipo in excluded:
                out.append(Violation(m.artefact, ipo, "excluded IPO used"))
            elif entry is None:
                out.append(Violation(m.artefact, ipo, "unknown ipo_id (not in splits.yaml)"))
            elif entry.slice == "test":
                out.append(Violation(m.artefact, ipo, "test/bench IPO"))
            elif entry.company_key in test_keys:
                twin = test_keys[entry.company_key]
                out.append(Violation(m.artefact, ipo, f"same company as test IPO {twin}"))
        if m.kind in ("train", "fit"):
            for name in m.inputs:
                if kinds.get(name) == "product_reference":
                    out.append(Violation(m.artefact, name, "product reference used as an input"))
    return out
