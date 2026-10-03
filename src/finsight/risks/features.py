"""Attach the B2.2 features to a document's risks: numbers, hedging, novelty."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from finsight.core.schemas import Risk
from finsight.risks.bank import RiskBank
from finsight.risks.hedging import hedging
from finsight.risks.novelty import embed_text, novelty
from finsight.risks.numbers import risk_numbers


class Embedder(Protocol):
    """bge-m3 (ONNX int8 on the CPU worker, or a GPU encoder); unit length not required."""

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """One unit-length vector per text."""


def add_features(
    risks: Sequence[Risk],
    company: str,
    *,
    bank: RiskBank | None = None,
    embedder: Embedder | None = None,
    tau: float = 0.80,
    nearest: int = 3,
    flag_min_hedges: int = 3,
) -> list[Risk]:
    """Copies of ``risks`` with numbers and hedging; novelty too when a bank and an embedder
    are given (without them ``novelty`` stays ``None`` and the UI hides the badge)."""
    out = []
    for r in risks:
        text = f"{r.title}. {r.body}"
        out.append(
            r.model_copy(
                update={
                    "numbers": risk_numbers(text),
                    "hedging": hedging(text, flag_min_hedges),
                }
            )
        )
    if bank is not None and embedder is not None and out:
        vectors = embedder.embed([embed_text(r.title, r.body) for r in out])
        for i, res in enumerate(novelty(vectors, bank, company, tau, nearest)):
            value = None if res.novelty != res.novelty else round(res.novelty, 4)
            out[i] = out[i].model_copy(update={"novelty": value, "nearest_examples": res.nearest})
    return out
