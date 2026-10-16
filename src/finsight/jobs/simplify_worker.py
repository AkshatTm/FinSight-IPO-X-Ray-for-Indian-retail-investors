"""The simplification queue worker (B02 §3.1, §8): top N by importance automatically, the rest
when a reader clicks "Explain in plain English" (``Database.bump`` moves it to the front).

One risk at a time on the CPU job (the student as GGUF Q4, ≈ 15 s each). Each result is saved to
``docs/<doc_id>/simplified.json`` straight away and announced with a ``risk_simplified`` event,
so the report fills in while the queue drains.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

from finsight.core.logging import get_logger
from finsight.db import Database
from finsight.storage import Storage, doc_key, get_json, put_json

logger = get_logger("finsight.jobs.simplify")
SIMPLIFIED = "simplified.json"
Emit = Callable[[str, dict[str, Any]], int]


class RewriteResult(Protocol):
    """What a simplifier returns: a status and a JSON-ready dict."""

    status: str

    def as_dict(self) -> dict[str, Any]:
        """The fields saved in ``simplified.json``."""


class RiskSimplifier(Protocol):
    """Rewrites one risk in plain English (see ``risks.Simplifier``)."""

    def rewrite(self, title: str, body: str) -> RewriteResult:
        """Rewrite a risk from its title and body."""


def _queue_status(simple_status: str) -> str:
    """The queue row's end state: ``done`` (ready or rejected) or ``failed`` (no answer)."""
    return "failed" if simple_status == "failed" else "done"


def auto_enqueue(db: Database, doc_id: str, ranked: Sequence[str], top_n: int) -> list[str]:
    """Queue the ``top_n`` most important risks (``ranked`` is most important first)."""
    picked = list(ranked[:top_n])
    db.enqueue(doc_id, picked)
    return picked


def load_simplified(storage: Storage, doc_id: str) -> dict[str, dict[str, Any]]:
    """The saved rewrites of a document by risk id (empty if none yet)."""
    key = doc_key(doc_id, SIMPLIFIED)
    return dict(get_json(storage, key)) if storage.exists(key) else {}


def run_queue(
    db: Database,
    storage: Storage,
    doc_id: str,
    risks: Mapping[str, tuple[str, str]],
    simplifier: RiskSimplifier,
    emit: Emit,
    *,
    max_items: int | None = None,
) -> dict[str, int]:
    """Drain the queue for one document; return counts per ``simple_status``.

    ``risks`` maps ``rid`` to ``(title, body)``. A queued id that is not a risk of this document
    ends as ``failed`` (it cannot be rewritten). A saved ``ready`` or ``rejected`` rewrite is not
    redone; a ``failed`` one is tried again.
    """
    saved = load_simplified(storage, doc_id)
    counts: dict[str, int] = {"ready": 0, "rejected": 0, "failed": 0}
    done = 0
    while max_items is None or done < max_items:
        rid = db.take_next(doc_id)
        if rid is None:
            break
        if rid in saved and saved[rid]["simple_status"] != "failed":  # a failure is retried
            db.finish_item(doc_id, rid, _queue_status(saved[rid]["simple_status"]))
            continue
        if rid not in risks:
            status = "failed"
            entry = {"simple": None, "simple_status": status, "reason": "unknown_risk"}
        else:
            title, body = risks[rid]
            result = simplifier.rewrite(title, body)
            status, entry = result.status, result.as_dict()
        saved[rid] = entry
        put_json(storage, doc_key(doc_id, SIMPLIFIED), saved)
        db.finish_item(doc_id, rid, _queue_status(status))
        emit("risk_simplified", {"rid": rid, "simple_status": status})
        counts[status] = counts.get(status, 0) + 1
        done += 1
    return counts


class SimplifyDrain:
    """Drains the simplification queue of a document on a background thread of the API process.

    ``kick`` after a job finishes (top-N queued) and after a click on "Explain in plain English".
    One thread per document at a time; the student model is built on the first rewrite, so
    nothing loads until a rewrite is wanted.
    """

    def __init__(
        self,
        db: Database,
        storage: Storage,
        make_simplifier: Callable[[], RiskSimplifier],
    ) -> None:
        self.db, self.storage, self._make = db, storage, make_simplifier
        self._simplifier: RiskSimplifier | None = None
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def kick(self, doc_id: str) -> bool:
        """Start draining ``doc_id`` unless a thread already is; True when one was started."""
        with self._lock:
            if doc_id in self._active:
                return False
            self._active.add(doc_id)
        threading.Thread(
            target=self._run, args=(doc_id,), name=f"simplify-{doc_id}", daemon=True
        ).start()
        return True

    def _run(self, doc_id: str) -> None:
        from finsight.core.schemas import Risk

        try:
            key = doc_key(doc_id, "risks.json")
            risks = [Risk.model_validate(r) for r in get_json(self.storage, key)]
            by_rid = {r.rid: (r.title, r.body) for r in risks}
            if self._simplifier is None:
                self._simplifier = self._make()
            job = self.db.latest_job(doc_id)

            def emit(event: str, data: dict[str, Any]) -> int:
                return self.db.append_event(job.job_id, event, data) if job else 0

            run_queue(self.db, self.storage, doc_id, by_rid, self._simplifier, emit)
        except Exception:  # a failed drain leaves the queue as it is; the next click retries
            logger.exception("simplify drain failed for %s", doc_id)
        finally:
            with self._lock:
                self._active.discard(doc_id)
            if self.db.waiting_rids(doc_id) and doc_id not in self._active:
                self.kick(doc_id)
