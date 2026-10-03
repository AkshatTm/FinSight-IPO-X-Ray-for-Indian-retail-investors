"""B2.6a: points, normalisation over available checks, percentile, thresholds, reasons."""

from pathlib import Path
from typing import Any

import pytest

from finsight.core.schemas import RedFlag, Risk
from finsight.risklevel import build, compute, level_for, load_config, percentile
from finsight.storage import LocalStorage, doc_key, get_json, put_json

CFG: dict[str, Any] = {
    "provisional": True,
    "corpus_n": 200,
    "points": {"concern": 2, "watch": 1, "risk": 1, "max_risk_points": 4},
    "unusual_below": 0.10,
    "thresholds": {"low_below": 0.2, "high_from": 0.4},
    "reference_quantiles": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "behind_click": False,
}


def flag(i: int, status: str) -> RedFlag:
    return RedFlag.model_validate(
        {"id": f"RF{i:02d}", "title": f"Flag {i}", "status": status, "sentence": "s"}
    )


def risk(i: int, seriousness: str | None, novelty: float | None) -> Risk:
    return Risk.model_validate(
        {
            "rid": f"r{i}",
            "order": i,
            "title": f"Risk {i}",
            "body": "b",
            "page_start": 1,
            "page_end": 1,
            "seriousness": seriousness,
            "novelty": novelty,
        }
    )


def test_points_and_normalisation() -> None:
    flags = [flag(1, "concern"), flag(2, "watch"), flag(3, "ok"), flag(4, "ok")]
    lvl = compute(flags, [], CFG)
    assert lvl.points == 3
    assert lvl.max_points == 2 * 4 + 4
    assert lvl.score == pytest.approx(3 / 12, abs=1e-4)
    assert lvl.checks_available == 4
    assert lvl.level == "medium"
    assert lvl.corpus_n == 200
    assert lvl.provisional
    assert lvl.disclaimer_key == "risklevel.disclaimer"


def test_unavailable_checks_leave_the_maximum_too() -> None:
    full = [flag(1, "concern")] + [flag(i, "ok") for i in range(2, 14)]
    na_heavy = [flag(1, "concern")] + [flag(i, "not_available") for i in range(2, 14)]
    a, b = compute(full, [], CFG), compute(na_heavy, [], CFG)
    assert a.points == b.points == 2
    assert (a.max_points, b.max_points) == (2 * 13 + 4, 2 * 1 + 4)
    # same evidence, fewer checks possible: the share reflects what could be checked
    assert b.checks_available == 1


def test_an_na_heavy_doc_with_nothing_found_is_not_inflated() -> None:
    lvl = compute([flag(i, "not_available") for i in range(1, 14)], [], CFG)
    assert lvl.points == 0
    assert lvl.score == 0.0
    assert lvl.level == "low"


def test_risk_points_need_high_seriousness_and_rarity_and_cap_at_four() -> None:
    risks = [
        risk(1, "high", 0.05),
        risk(2, "high", 0.09),
        risk(3, "high", 0.10),  # not below 10%
        risk(4, "medium", 0.01),
        risk(5, "high", None),
        *[risk(10 + i, "high", 0.01 * i) for i in range(5)],
    ]
    lvl = compute([], risks, CFG)
    assert lvl.points == 4
    assert lvl.max_points == 4
    assert [r.id for r in lvl.reasons] == ["r10", "r11", "r12", "r13"]  # rarest first
    assert lvl.reasons[0].link == "#risk-r10"


def test_reasons_put_concerns_first_with_links() -> None:
    lvl = compute([flag(2, "watch"), flag(1, "concern")], [risk(1, "high", 0.0)], CFG)
    assert [(r.source, r.id, r.points) for r in lvl.reasons] == [
        ("redflag", "RF01", 2),
        ("redflag", "RF02", 1),
        ("risk", "r1", 1),
    ]
    assert lvl.reasons[0].link == "#redflag-RF01"


@pytest.mark.parametrize(
    ("score", "pct"),
    [(0.0, 0.0), (-1.0, 0.0), (0.05, 5.0), (0.25, 25.0), (1.0, 100.0), (2.0, 100.0)],
)
def test_percentile(score: float, pct: float) -> None:
    assert percentile(score, CFG["reference_quantiles"]) == pct


def test_percentile_with_flat_steps_and_tiny_tables() -> None:
    assert percentile(0.2, [0.0, 0.2, 0.2, 1.0]) == pytest.approx(33.3, abs=0.1)
    assert percentile(0.5, [0.3]) == 0.0


def test_thresholds() -> None:
    t = CFG["thresholds"]
    assert level_for(0.19, t) == "low"
    assert level_for(0.2, t) == "medium"
    assert level_for(0.4, t) == "high"


def test_committed_config_is_marked_provisional() -> None:
    cfg = load_config()
    assert cfg["provisional"] is True
    q = cfg["reference_quantiles"]
    assert q == sorted(q)
    assert len(q) == 11


def test_build_reads_and_writes_storage(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    put_json(storage, doc_key("d", "redflags.json"), {"flags": [flag(1, "concern").model_dump()]})
    put_json(storage, doc_key("d", "risks.json"), [risk(1, "high", 0.01).model_dump()])
    lvl = build(storage, "d", CFG)
    assert lvl.points == 3
    assert get_json(storage, doc_key("d", "risklevel.json"))["points"] == 3
    assert build(storage, "empty", CFG).points == 0
