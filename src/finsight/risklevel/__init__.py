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
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from finsight.core.config import project_root
from finsight.core.schemas import (
    Level,
    RedFlag,
    Risk,
    RiskLevel,
    RiskLevelReason,
    SevereOverride,
)
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
    redflags: Sequence[RedFlag],
    risks: Sequence[Risk],
    cfg: dict[str, Any] | None = None,
    reference_scores: Sequence[float] | None = None,
    overrides: Sequence[SevereOverride] = (),
) -> RiskLevel:
    """Points from red flags and rare serious risks, normalised by available checks.

    ``reference_scores`` are the scores of the IPOs in the rolling reference window for this
    document's date (``finsight.risklevel.reference.window_scores``). When given, the percentile
    and ``corpus_n`` come from them instead of the stored deciles. ``overrides`` are the severe
    overrides of the document (C3.2): any one forces the high level, whatever the points say; the
    score and percentile are still computed from the points.
    """
    c = cfg if cfg is not None else load_config()
    quantiles, corpus_n = c["reference_quantiles"], int(c["corpus_n"])
    if reference_scores:
        from finsight.risklevel.reference import deciles

        quantiles, corpus_n = deciles(reference_scores), len(reference_scores)
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
    for o in overrides:
        reasons.append(
            RiskLevelReason(
                source="override", id=o.id, label=o.title, points=0, link=f"#severe-{o.id}"
            )
        )
    reasons.sort(key=lambda x: (x.source != "override", -x.points, x.source != "redflag", x.id))
    return RiskLevel(
        level="high" if overrides else level_for(score, c["thresholds"]),
        forced_by=[o.id for o in overrides],
        points=points,
        max_points=max_points,
        score=score,
        percentile=percentile(score, quantiles),
        checks_available=len(available),
        reasons=reasons,
        thresholds={k: float(v) for k, v in c["thresholds"].items()},
        corpus_n=corpus_n,
        provisional=bool(c["provisional"]),
        behind_click=bool(c["behind_click"]),
    )


def build(
    storage: Storage,
    doc_id: str,
    cfg: dict[str, Any] | None = None,
    *,
    company: str | None = None,
    scores_path: Path | None = None,
    as_of: date | None = None,
) -> RiskLevel:
    """The ``risk_level`` stage: read ``redflags.json`` and ``risks.json``, write
    ``risklevel.json``. A missing file counts as no flags or no risks.

    With ``scores_path`` (the reference IPOs' scores, ``reference_scores.csv``) the percentile is
    placed in the product reference window for ``as_of`` (default today), the issuer left out;
    without it the stored deciles are used.
    """
    flags_key, risks_key = doc_key(doc_id, "redflags.json"), doc_key(doc_id, "risks.json")
    flags_doc = get_json(storage, flags_key) if storage.exists(flags_key) else {"flags": []}
    flags = [RedFlag.model_validate(f) for f in flags_doc.get("flags", [])]
    overrides = [SevereOverride.model_validate(o) for o in flags_doc.get("severe_overrides", [])]
    risks = (
        [Risk.model_validate(r) for r in get_json(storage, risks_key)]
        if storage.exists(risks_key)
        else []
    )
    reference: list[float] | None = None
    if scores_path is not None and scores_path.exists():
        from finsight.risklevel.reference import read_scores, window_scores
        from finsight.splits import load_splits

        splits = load_splits(project_root() / "configs" / "splits.yaml")
        reference = window_scores(
            read_scores(scores_path),
            splits,
            as_of or date.today(),
            kind="product",
            exclude_company=company or None,
        )
    result = compute(flags, risks, cfg, reference_scores=reference, overrides=overrides)
    put_json(storage, doc_key(doc_id, RISKLEVEL_FILE), result.model_dump(mode="json"))
    return result


__all__ = ["RISKLEVEL_FILE", "build", "compute", "level_for", "load_config", "percentile"]
