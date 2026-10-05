"""The Phase 3 roadmap (C05) and the execution plan define the same parts (C_EXECUTION_PLAN §0)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHASE3 = ROOT / "docs" / "phase3"

ROADMAP_PART = re.compile(r"^- \[[ x]\] \*\*(C\d\.\d)\b")
PLAN_PART = re.compile(r"^(?:### (C\d\.\d)\b|- \*\*(C\d\.\d)\*\*)")


def _ids(path: Path, pattern: re.Pattern[str]) -> list[str]:
    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            ids.append(next(g for g in m.groups() if g))
    return ids


def test_roadmap_and_plan_define_the_same_parts() -> None:
    roadmap = _ids(PHASE3 / "C05_ROADMAP.md", ROADMAP_PART)
    plan = _ids(PHASE3 / "C_EXECUTION_PLAN.md", PLAN_PART)
    assert len(roadmap) > 25
    assert len(roadmap) == len(set(roadmap)), "duplicate part id in C05"
    assert len(plan) == len(set(plan)), "duplicate part id in C_EXECUTION_PLAN"
    assert set(roadmap) == set(plan)


def test_every_gate_has_a_review_line() -> None:
    text = (PHASE3 / "C05_ROADMAP.md").read_text(encoding="utf-8")
    for gate in range(7):
        assert f"**CG{gate}" in text, f"CG{gate} missing in C05"
