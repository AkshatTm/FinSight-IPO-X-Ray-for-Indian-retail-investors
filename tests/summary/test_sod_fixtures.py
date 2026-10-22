"""SOD engine against ARGON's gold (AR-02): ``data/gold/sod_fixtures/<ipo_id>/expected.json``.

Skipped until ARGON's ``expected.json`` files are merged from ``p4/argon``. Gate P4-G1: the engine
matches on at least 8 of the 10 fixture RHPs. ``expected.json`` maps field keys (the
``SODResult.fields()`` keys, e.g. ``revenue:latest``) to ``{"status": ..., "value": ...,
"page": ...}``; ``"not_in_sod"`` fields are not scored. A document passes when every scored field
has the expected status and, for numbers, the same value within 0.5%.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pytest
from real import loader

from finsight.core.config import project_root
from finsight.core.schemas import Count, Money, Percent, SummaryValue

GOLD = project_root() / "data" / "gold" / "sod_fixtures"
MIN_PASSING = 8
TOLERANCE = Decimal("0.005")


def _expected() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(GOLD.glob("*/expected.json")) if GOLD.exists() else []:
        out[path.parent.name] = json.loads(path.read_text("utf-8"))
    return out


def _number(v: SummaryValue) -> Decimal | None:
    if isinstance(v.value, Money):
        return v.value.value_inr
    if isinstance(v.value, Percent):
        return v.value.value
    if isinstance(v.value, Count):
        return Decimal(v.value.value)
    return None


def _matches(got: SummaryValue | None, want: dict[str, Any]) -> bool:
    status = want.get("status", "found")
    if got is None:
        return status == "not_found"
    if got.status != status:
        return False
    if want.get("value") is None:
        return True
    value = _number(got)
    try:
        target = Decimal(str(want["value"]))
    except InvalidOperation:
        return False
    if value is None:
        return False
    return abs(value - target) <= abs(target) * TOLERANCE


def _score(ipo_id: str, expected: dict[str, Any]) -> list[str]:
    from finsight.summary import extract_summary
    from finsight.summary.sod import build_sod

    doc = loader.load_doc(ipo_id, root=loader.SOD)
    sections = loader.load_sections(ipo_id, root=loader.SOD)
    summary = extract_summary(doc, sections, ipo_id)
    fields = build_sod(doc, sections, summary, ipo_id).fields()
    wanted = expected.get("fields", expected)
    return [
        key for key, want in wanted.items()
        if isinstance(want, dict) and want.get("status") != "not_in_sod"
        and not _matches(fields.get(key), want)
    ]  # fmt: skip


def test_sod_engine_passes_argons_fixtures_on_at_least_eight_of_ten() -> None:
    expected = _expected()
    if not expected:
        pytest.skip("ARGON's SOD fixtures (expected.json) are not merged yet")
    missing = [i for i in expected if not (loader.SOD / i / "rhp.pages.json.gz").exists()]
    assert not missing, f"no exported pages for {missing}"
    failures = {ipo: bad for ipo, exp in expected.items() if (bad := _score(ipo, exp))}
    passing = len(expected) - len(failures)
    assert passing >= min(MIN_PASSING, len(expected)), json.dumps(failures, indent=1)


def test_fixture_files_parse_when_present() -> None:
    for ipo_id, data in _expected().items():
        assert isinstance(data, dict), ipo_id
    assert Path(GOLD).name == "sod_fixtures"
