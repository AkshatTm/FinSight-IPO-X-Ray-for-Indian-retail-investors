"""Risks endpoints (B06 §3): the list with sort and filters, one risk, and "explain this one".

Risks come from ``docs/<doc_id>/risks.json`` (written by the risks stages); plain-English
rewrites are merged in from ``simplified.json`` as the queue fills it (B2.5).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request
from pydantic import BaseModel

from finsight.api.errors import ApiError, ErrorResponse
from finsight.api.routes_docs import _doc
from finsight.api.uploads_state import UState
from finsight.core.schemas import (
    Compare,
    RedFlags,
    Risk,
    RiskCategory,
    RiskLevel,
    SimpleStatus,
)
from finsight.jobs import load_simplified
from finsight.risklevel import RISKLEVEL_FILE
from finsight.risklevel import load_config as risklevel_config
from finsight.risks import risks_config
from finsight.storage import doc_key, get_json

router = APIRouter(
    prefix="/api",
    responses={"4XX": {"model": ErrorResponse}, "5XX": {"model": ErrorResponse}},
)

DocId = Annotated[str, Path(min_length=1, max_length=40)]
Rid = Annotated[str, Path(min_length=1, max_length=64)]
BODY_PREVIEW = 1200
SIMPLIFY_PER_MINUTE = 20  # per IP (B06 §1: auth optional, rate-limited)


class CategoryCount(BaseModel):
    category: RiskCategory | None
    count: int


class RisksPage(BaseModel):
    n_total: int  # every risk in the document, before filters
    groups: list[CategoryCount]  # counts per category over all risks (the filter chips)
    risks: list[Risk]


class SimplifyQueued(BaseModel):
    rid: str
    simple_status: SimpleStatus
    position: int  # 0 = next; -1 = not queued (already explained)


def load_risks(state: UState, doc_id: str) -> list[Risk]:
    _doc(state, doc_id)
    key = doc_key(doc_id, "risks.json")
    if not state.storage.exists(key):
        raise ApiError(404, "not_available", "The risks for this report aren't ready yet.")
    risks = [Risk.model_validate(r) for r in get_json(state.storage, key)]
    simplified = load_simplified(state.storage, doc_id)
    out = []
    for r in risks:
        s = simplified.get(r.rid)
        if s:
            r = r.model_copy(
                update={"simple": s.get("simple"), "simple_status": s["simple_status"]}
            )
        out.append(r)
    return out


def _sorted(risks: list[Risk], sort: str) -> list[Risk]:
    if sort == "order":
        return sorted(risks, key=lambda r: r.order)
    if sort == "category":
        return sorted(risks, key=lambda r: (r.category or "~", r.order))
    # importance: highest first; risks without a score keep document order after the rest
    return sorted(risks, key=lambda r: (r.importance is None, -(r.importance or 0.0), r.order))


@router.get("/docs/{doc_id}/risks", tags=["risks"])
def list_risks(
    doc_id: DocId,
    state: UState,
    sort: Literal["importance", "order", "category"] = "importance",
    category: RiskCategory | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    unusual_only: bool = False,
) -> RisksPage:
    risks = load_risks(state, doc_id)
    counts: dict[RiskCategory | None, int] = defaultdict(int)
    for r in risks:
        counts[r.category] += 1
    groups = [CategoryCount(category=c, count=n) for c, n in counts.items()]
    groups.sort(key=lambda g: (-g.count, g.category or "~"))
    picked = risks
    if category:
        picked = [r for r in picked if r.category == category]
    if unusual_only:
        below = float(risks_config()["novelty"]["unusual_below"])
        picked = [r for r in picked if r.novelty is not None and r.novelty < below]
    if q and q.strip():
        needle = q.strip().lower()
        picked = [r for r in picked if needle in f"{r.title}\n{r.body}\n{r.simple or ''}".lower()]
    page = [
        r.model_copy(update={"body": r.body[:BODY_PREVIEW]}) if len(r.body) > BODY_PREVIEW else r
        for r in _sorted(picked, sort)
    ]
    return RisksPage(n_total=len(risks), groups=groups, risks=page)


def _risk(state: UState, doc_id: str, rid: str) -> Risk:
    for r in load_risks(state, doc_id):
        if r.rid == rid:
            return r
    raise ApiError(404, "risk_not_found", "We couldn't find this risk in the report.")


@router.get("/docs/{doc_id}/risks/{rid}", tags=["risks"])
def get_risk(doc_id: DocId, rid: Rid, state: UState) -> Risk:
    """The full risk, with its nearest past examples."""
    return _risk(state, doc_id, rid)


class _RateLimit:
    """A sliding one-minute window per client IP, in process memory (one API instance)."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] >= 60.0:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True


simplify_limit = _RateLimit(SIMPLIFY_PER_MINUTE)


@router.post("/docs/{doc_id}/risks/{rid}/simplify", tags=["risks"])
def simplify_risk(doc_id: DocId, rid: Rid, state: UState, request: Request) -> SimplifyQueued:
    """Queue a risk for a plain-English rewrite, or move it to the front of the queue."""
    ip = request.client.host if request.client else "unknown"
    if not simplify_limit.allow(ip):
        raise ApiError(429, "rate_limited", "Too many requests. Please wait a minute.")
    risk = _risk(state, doc_id, rid)
    if risk.simple_status in ("ready", "rejected"):
        return SimplifyQueued(rid=rid, simple_status=risk.simple_status, position=-1)
    position = state.db.bump(doc_id, rid)
    return SimplifyQueued(rid=rid, simple_status="pending", position=position)


@router.get("/docs/{doc_id}/risk-level", tags=["risks"])
def get_risk_level(doc_id: DocId, state: UState) -> RiskLevel:
    """The level with its reasons (B02 §7.4). ``behind_click`` follows the current config, so the
    teacher's "hide it" switch works without recomputing reports."""
    _doc(state, doc_id)
    key = doc_key(doc_id, RISKLEVEL_FILE)
    if not state.storage.exists(key):
        raise ApiError(404, "not_available", "The risk level for this report isn't ready yet.")
    level = RiskLevel.model_validate(get_json(state.storage, key))
    return level.model_copy(update={"behind_click": bool(risklevel_config()["behind_click"])})


@router.get("/docs/{doc_id}/compare", tags=["risks"])
def get_compare(doc_id: DocId, state: UState) -> Compare:
    """Listed peers from the document and percentiles among past IPOs (B05 §5.6)."""
    _doc(state, doc_id)
    key = doc_key(doc_id, "compare.json")
    if not state.storage.exists(key):
        raise ApiError(404, "not_available", "The comparison for this report isn't ready yet.")
    return Compare.model_validate(get_json(state.storage, key))


@router.get("/docs/{doc_id}/redflags", tags=["risks"])
def get_redflags(doc_id: DocId, state: UState) -> RedFlags:
    """The 13 red-flag checks with their numbers and evidence (B01 §5, B05 §5.4)."""
    _doc(state, doc_id)
    key = doc_key(doc_id, "redflags.json")
    if not state.storage.exists(key):
        raise ApiError(404, "not_available", "The red flags for this report aren't ready yet.")
    return RedFlags.model_validate(get_json(state.storage, key))
