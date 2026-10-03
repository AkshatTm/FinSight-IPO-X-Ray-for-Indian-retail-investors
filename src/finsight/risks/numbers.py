"""Numbers stated in a risk factor (B02 §5 ``Risk.numbers``), read with the shared normalizer."""

from __future__ import annotations

from finsight.core.schemas import Amount
from finsight.normalize import parse_amounts


def risk_numbers(text: str) -> list[Amount]:
    """Money, percentages and counts in ``text``, in order, each value once."""
    out: list[Amount] = []
    seen: set[str] = set()
    for span in parse_amounts(text):
        key = span.amount.model_dump_json(exclude={"raw"})
        if key in seen:
            continue
        seen.add(key)
        out.append(span.amount)
    return out
