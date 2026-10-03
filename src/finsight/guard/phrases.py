"""Forbidden-phrase filter (B01 §6, B-ADR-13), shared by UI copy tests and model rewrites.

    hits = find_forbidden("You should apply for this IPO.")   # -> [PhraseHit("tell_to_trade", ...)]

Allow-listed fixed lines (the disclaimer, "selling shareholders", ...) are blanked out first, so
they never match. Patterns live in ``configs/forbidden_phrases.yaml``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from finsight.core.config import project_root


@dataclass(frozen=True)
class PhraseHit:
    """A forbidden phrase found in a text: its rule id and the matched words."""

    id: str
    text: str


@dataclass(frozen=True)
class PhraseList:
    """Compiled forbidden-phrase patterns and the allowed exceptions."""

    allow: tuple[re.Pattern[str], ...]
    patterns: tuple[tuple[str, re.Pattern[str]], ...]


def default_path() -> Path:
    """``configs/forbidden_phrases.yaml``."""
    return project_root() / "configs" / "forbidden_phrases.yaml"


@lru_cache(maxsize=4)
def load_phrases(path: Path | None = None) -> PhraseList:
    """Compile the phrase list (cached per path)."""
    raw = yaml.safe_load((path or default_path()).read_text(encoding="utf-8"))
    allow = tuple(re.compile(re.escape(a), re.IGNORECASE) for a in raw.get("allow", []))
    patterns = tuple(
        (p["id"], re.compile(p["regex"], re.IGNORECASE | re.MULTILINE)) for p in raw["patterns"]
    )
    return PhraseList(allow, patterns)


def find_forbidden(text: str, phrases: PhraseList | None = None) -> list[PhraseHit]:
    """Every forbidden phrase in ``text`` (empty when the text is clean)."""
    rules = phrases or load_phrases()
    cleaned = text.replace("’", "'")
    for allowed in rules.allow:
        cleaned = allowed.sub(" ", cleaned)
    hits = []
    for pid, pattern in rules.patterns:
        match = pattern.search(cleaned)
        if match:
            hits.append(PhraseHit(pid, match.group(0).strip()))
    return hits


def is_clean(text: str) -> bool:
    """True when the text has no forbidden phrase."""
    return not find_forbidden(text)
