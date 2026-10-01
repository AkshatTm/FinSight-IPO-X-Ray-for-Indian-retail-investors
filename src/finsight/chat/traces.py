"""Trace store: one SQLite row per answered question (``GET /api/traces/{id}``, the Inspector).

A trace holds what the Inspector shows: stages, every passage seen (including dropped ones), the
exact prompt, the number checks and the timings. It is saved for every turn, also refusals and
abstentions, so "how was this made" always has an answer.
"""

from __future__ import annotations

import secrets
import sqlite3
import time
from pathlib import Path

from finsight.core.schemas import Trace

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32, as ULIDs use


def new_trace_id(now_ms: int | None = None) -> str:
    """A 26-character ULID: 48-bit millisecond time then 80 random bits, sortable by time."""
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    value = (now << 80) | secrets.randbits(80)
    return "".join(_ALPHABET[(value >> shift) & 31] for shift in range(125, -1, -5))


class TraceStore:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory = sqlite3.connect(":memory:") if self.path == ":memory:" else None
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS traces ("
                "trace_id TEXT PRIMARY KEY, ipo_id TEXT NOT NULL, created_ms INTEGER NOT NULL, "
                "body TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return self._memory or sqlite3.connect(self.path)

    def save(self, ipo_id: str, trace: Trace) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO traces VALUES (?, ?, ?, ?)",
                (trace.trace_id, ipo_id, int(time.time() * 1000), trace.model_dump_json()),
            )

    def get(self, trace_id: str) -> Trace | None:
        with self._connect() as db:
            row = db.execute("SELECT body FROM traces WHERE trace_id = ?", (trace_id,)).fetchone()
        return Trace.model_validate_json(row[0]) if row else None

    def count(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM traces").fetchone()[0])
