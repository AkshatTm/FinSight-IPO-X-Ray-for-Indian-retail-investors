"""Risk level (B02 §7.4, B-ADR-11): red-flag and risk points as a share of the points possible
over the checks available for this document, placed among past IPOs (2018-2023).

Concern = 2, Watch = 1; each high-seriousness risk found in fewer than 10% of past IPOs = 1 (at
most 4). Checks that are not available or not applicable count in neither the points nor the
maximum, so documents with fewer disclosures are not pushed down (or up). The level is a
description of what the document discloses, never a recommendation; the disclaimer always goes
with it.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from finsight.core.config import project_root
from finsight.core.schemas import Level, RedFlag, Risk, RiskLevel, RiskLevelReason
from finsight.storage import Storage, doc_key, get_json, put_json

RISKLEVEL_FILE = "risklevel.json"
UNAVAILABLE = ("not_available", "not_applicable")


@lru_cache(maxsize=4)
def load_config(path: Path | None = None) -> dict[str, Any]:
    """The risk-level settings (``configs/risklevel.yaml``)."""
    cfg: dict[str, Any] = yaml.safe_load(
        (path or project_root() / "configs" / "risklevel.yaml").read_text(encoding="utf-8")
    )
    return cfg


def percentile(score: float, quantiles: Sequence[float]) -> float:
    """Share (0-100) of reference IPOs below ``score``, interpolated between the stored
    deciles (``quantiles[i]`` is the score at percentile ``100 * i / (len - 1)``)."""
    q = list(quantiles)
    if len(q) < 2:
        return 0.0
    step = 100.0 / (len(q) - 1)
    if score <= q[0]:
        return 0.0
    if score >= q[-1]:
        return 100.0
    i = bisect_left(q, score)  # q[i-1] < score <= q[i]
    lo, hi = q[i - 1], q[i]
    frac = 0.0 if hi == lo else (score - lo) / (hi - lo)
    return round((i - 1 + frac) * step, 1)


def level_for(score: float, thresholds: dict[str, float]) -> Level:
    """Low below ``low_below``, high from ``high_from``, else medium."""
    if score < thresholds["low_below"]:
        return "low"
    if score >= thresholds["high_from"]:
        return "high"
    return "medium"


def compute(
    redflags: Sequence[RedFlag], risks: Sequence[Risk], cfg: dict[str, Any] | None = None
) -> RiskLevel:
    """Points from red flags and rare serious risks, normalised by available checks."""
    c = cfg if cfg is not None else load_config()
    pts = c["points"]
    reasons: list[RiskLevelReason] = []
    available = [f for f in redflags if f.status not in UNAVAILABLE]
    points = 0
    for f in available:
        p = (
            int(pts["concern"])
            if f.status == "concern"
            else int(pts["watch"])
            if f.status == "watch"
            else 0
        )
        if p:
            points += p
            reasons.append(
                RiskLevelReason(
                    source="redflag", id=f.id, label=f.title, points=p, link=f"#redflag-{f.id}"
                )
            )
    rare = [
        r
        for r in sorted(risks, key=lambda r: (r.novelty if r.novelty is not None else 1.0, r.order))
        if r.seriousness == "high"
        and r.novelty is not None
        and r.novelty < float(c["unusual_below"])
    ][: int(pts["max_risk_points"])]
    for r in rare:
        points += int(pts["risk"])
        reasons.append(
            RiskLevelReason(
                source="risk",
                id=r.rid,
                label=r.title,
                points=int(pts["risk"]),
                link=f"#risk-{r.rid}",
            )
        )
    max_points = int(pts["concern"]) * len(available) + int(pts["risk"]) * int(
        pts["max_risk_points"]
    )
    score = round(points / max_points, 4) if max_points else 0.0
    reasons.sort(key=lambda x: (-x.points, x.source != "redflag", x.id))
    return RiskLevel(
        level=level_for(score, c["thresholds"]),
        points=points,
        max_points=max_points,
        score=score,
        percentile=percentile(score, c["reference_quantiles"]),
        checks_available=len(available),
        reasons=reasons,
        thresholds={k: float(v) for k, v in c["thresholds"].items()},
        corpus_n=int(c["corpus_n"]),
        provisional=bool(c["provisional"]),
        behind_click=bool(c["behind_click"]),
    )


def build(storage: Storage, doc_id: str, cfg: dict[str, Any] | None = None) -> RiskLevel:
    """The ``risk_level`` stage: read ``redflags.json`` and ``risks.json``, write
    ``risklevel.json``. A missing file counts as no flags or no risks."""
    flags_key, risks_key = doc_key(doc_id, "redflags.json"), doc_key(doc_id, "risks.json")
    flags_doc = get_json(storage, flags_key) if storage.exists(flags_key) else {"flags": []}
    flags = [RedFlag.model_validate(f) for f in flags_doc.get("flags", [])]
    risks = (
        [Risk.model_validate(r) for r in get_json(storage, risks_key)]
        if storage.exists(risks_key)
        else []
    )
    result = compute(flags, risks, cfg)
    put_json(storage, doc_key(doc_id, RISKLEVEL_FILE), result.model_dump(mode="json"))
    return result


__all__ = ["RISKLEVEL_FILE", "build", "compute", "level_for", "load_config", "percentile"]
