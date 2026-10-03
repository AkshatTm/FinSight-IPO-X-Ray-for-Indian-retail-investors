"""B2.5a: the simplification queue (top N automatic, click bump) and its events."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from finsight.db import Database
from finsight.db.tables import simplify_queue
from finsight.jobs.simplify_worker import SIMPLIFIED, auto_enqueue, load_simplified, run_queue
from finsight.storage import LocalStorage


@dataclass
class Result:
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {"simple": "x" if self.status == "ready" else None, "simple_status": self.status}


class Fake:
    def __init__(self, status: dict[str, str] | None = None) -> None:
        self.seen: list[str] = []
        self.status = status or {}

    def rewrite(self, title: str, body: str) -> Result:
        self.seen.append(title)
        return Result(self.status.get(title, "ready"))


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{(tmp_path / 's.db').as_posix()}")
    database.create_all()
    return database


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "store")


RISKS = {f"r{i}": (f"r{i}", f"body {i}") for i in range(20)}
RANKED = [f"r{i}" for i in range(20)]


def test_top_n_queued_then_a_click_jumps_the_queue(db: Database, storage: LocalStorage) -> None:
    assert auto_enqueue(db, "doc", RANKED, 15) == RANKED[:15]
    events: list[tuple[str, dict[str, Any]]] = []
    fake = Fake()
    emit = lambda e, d: events.append((e, d)) or len(events)  # noqa: E731
    run_queue(db, storage, "doc", RISKS, fake, emit, max_items=2)
    assert fake.seen == ["r0", "r1"]
    db.bump("doc", "r18")  # outside the top 15: the click adds it at the front
    counts = run_queue(db, storage, "doc", RISKS, fake, emit)
    assert fake.seen[2] == "r18"
    assert len(fake.seen) == 16
    assert counts == {"ready": 14, "rejected": 0, "failed": 0}
    assert events[0] == ("risk_simplified", {"rid": "r0", "simple_status": "ready"})
    assert set(load_simplified(storage, "doc")) == set(RANKED[:15]) | {"r18"}
    assert db.queue("doc") == []


def test_statuses_unknown_ids_and_retry_of_failures(db: Database, storage: LocalStorage) -> None:
    db.enqueue("doc", ["r1", "r2", "r3", "nope"])
    fake = Fake({"r2": "rejected", "r3": "failed"})
    counts = run_queue(db, storage, "doc", RISKS, fake, lambda e, d: 0)
    assert counts == {"ready": 1, "rejected": 1, "failed": 2}
    saved = load_simplified(storage, "doc")
    assert saved["nope"]["reason"] == "unknown_risk"
    assert storage.exists(f"docs/doc/{SIMPLIFIED}")
    # a later run: the ready and rejected ones are not redone, the failed one is retried
    fake2 = Fake()
    with db.engine.begin() as conn:  # re-queue everything, as a retried job would
        conn.execute(simplify_queue.update().values(status="queued"))
    run_queue(db, storage, "doc", RISKS, fake2, lambda e, d: 0)
    assert fake2.seen == ["r3"]
