"""Rule-based seriousness and importance (B02 §7.3), transparent by design.

score = the category's base weight + 1 if the risk states a hard fact + 1 if it states a material
number - 1 if it is boilerplate (novelty above 0.8). High at 3+, medium at 2, low below.
Importance (the sort order) = seriousness weight x (1 - novelty). The teacher's 1-5 ratings only
*check* this rule (E17, B2.6b); they never train it.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from finsight.core.schemas import Risk, Seriousness
from finsight.risks.bank import risks_config


def _cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    return dict(cfg if cfg is not None else risks_config()["seriousness"])


def material_number(risk: Risk, cfg: dict[str, Any], reference_inr: Decimal | None = None) -> bool:
    """A stated percentage >= ``material_percent``, or an amount >= ``material_share`` of the
    company's revenue or net worth when that reference is known."""
    for n in risk.numbers:
        if n.kind == "percent" and Decimal(n.value) >= Decimal(str(cfg["material_percent"])):
            return True
        share = Decimal(str(cfg["material_share"]))
        if (
            n.kind == "money"
            and reference_inr is not None
            and n.value_inr is not None
            and Decimal(n.value_inr) >= share * reference_inr
        ):
            return True
    return False


def seriousness_score(
    risk: Risk, cfg: dict[str, Any] | None = None, reference_inr: Decimal | None = None
) -> int:
    c = _cfg(cfg)
    score = int(
        c["base"].get(risk.category, c["unknown_category"])
        if risk.category
        else c["unknown_category"]
    )
    score += int(risk.hedging.hard_fact)
    score += int(material_number(risk, c, reference_inr))
    if risk.novelty is not None and risk.novelty > float(c["boilerplate_novelty"]):
        score -= 1
    return score


def seriousness(score: int, cfg: dict[str, Any] | None = None) -> Seriousness:
    c = _cfg(cfg)
    if score >= int(c["high_at"]):
        return "high"
    if score >= int(c["medium_at"]):
        return "medium"
    return "low"


def importance(
    level: Seriousness, novelty: float | None, cfg: dict[str, Any] | None = None
) -> float:
    c = _cfg(cfg)
    rarity = 1.0 - (novelty if novelty is not None else float(c["unknown_novelty"]))
    return round(float(c["weights"][level]) * rarity, 4)


def score_risks(
    risks: Sequence[Risk],
    cfg: dict[str, Any] | None = None,
    reference_inr: Decimal | None = None,
) -> list[Risk]:
    """Copies of ``risks`` with ``seriousness`` and ``importance`` set."""
    out = []
    for r in risks:
        level = seriousness(seriousness_score(r, cfg, reference_inr), cfg)
        out.append(
            r.model_copy(
                update={"seriousness": level, "importance": importance(level, r.novelty, cfg)}
            )
        )
    return out


def ranked_rids(risks: Sequence[Risk]) -> list[str]:
    """Most important first, ties in document order (the simplify queue's order)."""
    ordered = sorted(risks, key=lambda r: (r.importance is None, -(r.importance or 0.0), r.order))
    return [r.rid for r in ordered]
