"""Keep demo and gold-v2 IPOs out of the training corpus (ADR-016, 05 section 1.3).

A company that appears in both training text and the evaluation set would make scores look
better than they are. Names are compared after ``normalize_company`` (lowercase, no "IPO",
"Limited"/"Ltd" or punctuation). Two names match when they are the same, differ only in
spacing ("Urbancompany" vs "Urban Company"), or one is a single distinctive word that opens
the other ("Groww" vs "Groww Innovations"). "Tata Capital" does not match "Tata Motors".
"""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path

from finsight.core.config import get_settings
from finsight.ingest.recon import normalize_company
from finsight.ingest.registry import list_demo_ipos

SIMILARITY = 0.9  # SequenceMatcher ratio on names with the spaces removed


def matches(corpus_name: str, excluded_name: str) -> bool:
    a, b = normalize_company(corpus_name), normalize_company(excluded_name)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = sorted((a.split(), b.split()), key=len)
    if len(short) == 1 and long_[0] == short[0]:
        return True  # one distinctive word opens the longer name
    return SequenceMatcher(None, a.replace(" ", ""), b.replace(" ", "")).ratio() >= SIMILARITY


def is_excluded(corpus_name: str, excluded: list[str]) -> str | None:
    """The excluded name that ``corpus_name`` matches, else None."""
    return next((name for name in excluded if matches(corpus_name, name)), None)


def load_gold_names(path: Path) -> list[str]:
    """Company names in ``data/gold/excluded_ipos.txt`` (one per line, ``#`` comments)."""
    if not path.exists():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def excluded_names(gold_file: Path | None = None) -> list[str]:
    """Every demo company plus the gold-v2 companies listed in the exclusion file."""
    path = gold_file or get_settings().paths.gold_dir / "excluded_ipos.txt"
    return [ipo.company for ipo in list_demo_ipos()] + load_gold_names(path)
