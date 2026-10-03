"""Certainty check (B01 §6 rule 5): "may" stays "may"; "has happened" stays "has happened".

A rewrite fails when it drops every hedge of a hedged original (may → will), adds definite
words the original did not use, or hedges an original that stated a fact.
"""

from __future__ import annotations

import re

HEDGES = (
    "may",
    "might",
    "could",
    "can",
    "possibly",
    "possible",
    "potential",
    "potentially",
    "likely",
    "unlikely",
    "uncertain",
    "if",
    "risk",
    "there is no assurance",
    "cannot assure",
    "no assurance",
)
DEFINITE = ("will", "definitely", "certainly", "surely", "always", "never", "guaranteed")


def _has(words: tuple[str, ...], text: str) -> set[str]:
    low = text.lower().replace("’", "'")
    return {w for w in words if re.search(rf"\b{re.escape(w)}\b", low)}


def certainty_changed(original: str, rewrite: str) -> str | None:
    """A short reason when the rewrite changes how certain the statement is, else ``None``."""
    src_h, out_h = _has(HEDGES, original), _has(HEDGES, rewrite)
    src_d, out_d = _has(DEFINITE, original), _has(DEFINITE, rewrite)
    if src_h and not out_h:
        return "hedge_dropped"
    if out_d - src_d:
        return "definite_added"
    if not src_h and out_h - {"risk", "if"}:
        return "hedge_added"
    return None
