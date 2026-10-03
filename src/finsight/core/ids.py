"""Identifier helpers: IPO slugs, document ids, passage ids and time-sortable trace ids."""

from __future__ import annotations

import re
from typing import get_args

from ulid import ULID

from finsight.core.schemas import DocType

_LEGAL_SUFFIX = re.compile(r"\b(limited|ltd)\b\.?$", re.IGNORECASE)
_PASSAGE = re.compile(r"^(?P<ipo>[^:]+)(?::(?P<doc>prospectus|drhp))?:p(?P<page>\d+):c(?P<k>\d+)$")


def new_trace_id() -> str:
    """A ULID: 26 characters, sortable by creation time."""
    return str(ULID())


def make_ipo_id(company: str, year: int) -> str:
    """``"Acme Industries Ltd", 2025`` -> ``"acme-industries-2025"``."""
    name = _LEGAL_SUFFIX.sub("", company.strip()).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{slug}-{year}"


def make_doc_id(sha256: str) -> str:
    """``"doc_"`` + the first 16 hex characters of the file's SHA-256.

    Same bytes give the same id, which is how uploads are deduplicated (B-FR-01).
    """
    digest = sha256.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("sha256 must be 64 hex characters")
    return f"doc_{digest[:16]}"


def passage_id(ipo_id: str, doc_type: DocType, page_start: int, k: int) -> str:
    """``<ipo_id>:p<page>:c<k>`` for RHP passages (02 section 9).

    Prospectus and DRHP passages add ``:prospectus`` / ``:drhp`` after the IPO id,
    because every document has a page 12 (ADR-033).
    """
    if doc_type not in get_args(DocType):
        raise ValueError(f"Unknown doc_type {doc_type!r}")
    prefix = ipo_id if doc_type == "rhp" else f"{ipo_id}:{doc_type}"
    return f"{prefix}:p{page_start}:c{k}"


def parse_passage_id(pid: str) -> tuple[str, DocType, int, int]:
    match = _PASSAGE.match(pid)
    if not match:
        raise ValueError(f"Not a valid passage id: {pid!r}")
    doc: DocType = "rhp"
    if match["doc"] == "prospectus":
        doc = "prospectus"
    elif match["doc"] == "drhp":
        doc = "drhp"
    return match["ipo"], doc, int(match["page"]), int(match["k"])
