"""Tables in the key sections, with the unit header ("₹ in million") that scales their cells."""

from __future__ import annotations

import re

_CUR = re.compile(r"(₹|\bRs\b\.?|\bINR\b|\bRupees\b|US\$|\bUSD\b)", re.IGNORECASE)
_SCALE = re.compile(
    r"(\blakhs?\b|\blacs?\b|\bcrores?\b|\bcr\b|\bmillions?\b|\bmn\b|\bbillions?\b|\bbn\b"
    r"|\bthousands?\b|['’‘]000\b)",
    re.IGNORECASE,
)
_SCALE_NAMES = {
    "lakh": "lakh", "lac": "lakh", "crore": "crore", "cr": "crore",
    "million": "million", "mn": "million", "billion": "billion", "bn": "billion",
    "thousand": "thousand", "000": "thousand",
}  # fmt: skip
_PAREN = re.compile(r"\(([^()]*)\)")
_BARE = re.compile(r"^\s*(in\s+)?(₹|Rs\.?|INR)\s+(in\s+)?\w+\s*$", re.IGNORECASE)


def _scale_name(token: str) -> str:
    word = token.lower().lstrip("'’‘").rstrip("s")
    return _SCALE_NAMES[word]


def _unit(text: str, *, need_in: bool) -> str | None:
    """ "₹ in million" for a unit phrase like "Amount in ₹ crores"; None if it is not one."""
    if re.search(r"\d", text.replace("000", "")):
        return None  # "(₹ 800 crore)" is an amount, not a unit header
    cur, scale = _CUR.search(text), _SCALE.search(text)
    has_in = re.search(r"\bin\b", text, re.IGNORECASE) is not None
    if not cur and not (scale and has_in):
        return None
    if need_in and not (cur and scale):
        return None
    sym = None if not cur else ("$" if "$" in cur[0] or "usd" in cur[0].lower() else "₹")
    if scale is None:
        return sym
    return f"{sym} in {_scale_name(scale[0])}" if sym else f"in {_scale_name(scale[0])}"


def detect_header_scale(text: str) -> str | None:
    """First unit header in ``text`` (table header cells or the lines just above a table)."""
    for line in text.splitlines():
        for group in _PAREN.findall(line):
            if unit := _unit(group, need_in=False):
                return unit
        if _BARE.match(line) and (unit := _unit(line, need_in=True)):
            return unit
    return None
