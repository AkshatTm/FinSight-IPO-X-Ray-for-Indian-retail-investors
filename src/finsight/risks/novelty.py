"""How common a risk is among past IPOs (B02 §7.1).

``novelty`` = share of distinct past companies (2018-2023, the issuer itself excluded) with at
least one risk at cosine similarity >= tau. Low novelty = unusual. The card shows up to 3 of the
most similar past risks, one per company. Embedding text = title + first 2 sentences.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from finsight.core.schemas import NearestExample
from finsight.risks.bank import RiskBank, company_key, normalise

_SENTENCES = re.compile(r"(?<=[.!?])\s+")


def embed_text(title: str, body: str, sentences: int = 2) -> str:
    """What is embedded for a risk (both for the bank and for a new document)."""
    first = " ".join(_SENTENCES.split(body.strip())[:sentences])
    title = title.strip().rstrip(".")
    return f"{title}. {first}" if title else first


@dataclass(frozen=True)
class NoveltyResult:
    """Novelty of one risk and its nearest past examples."""

    novelty: float
    nearest: list[NearestExample]


def novelty(
    queries: np.ndarray,
    bank: RiskBank,
    company: str,
    tau: float,
    nearest: int = 3,
) -> list[NoveltyResult]:
    """One result per query row (``nan`` novelty when no other company is in the bank)."""
    keys = np.array(bank.keys())
    own = company_key(company)
    mask = keys != own
    ref_keys = keys[mask]
    vectors = bank.vectors[mask]
    rows = np.flatnonzero(mask)
    n_companies = len(set(ref_keys.tolist()))
    sims = normalise(queries) @ vectors.T if len(vectors) else np.zeros((len(queries), 0))
    out = []
    for q in range(sims.shape[0]):
        s = sims[q]
        hit = set(ref_keys[s >= tau].tolist())
        value = len(hit) / n_companies if n_companies else float("nan")
        examples: list[NearestExample] = []
        seen: set[str] = set()
        for j in np.argsort(-s):
            key = ref_keys[j]
            if key in seen:
                continue
            seen.add(key)
            i = rows[j]
            examples.append(
                NearestExample(
                    company=bank.companies[i],
                    year=int(bank.years[i]),
                    title=bank.titles[i],
                    similarity=round(float(s[j]), 4),
                )
            )
            if len(examples) >= nearest:
                break
        out.append(NoveltyResult(value, examples))
    return out


def unusualness_label(value: float | None, unusual_below: float, common_above: float) -> str | None:
    """B05 §6 badge kind: ``unusual``, ``common`` or ``neutral`` (``None`` without novelty)."""
    if value is None or value != value:  # nan
        return None
    if value < unusual_below:
        return "unusual"
    if value > common_above:
        return "common"
    return "neutral"
