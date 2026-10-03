"""Demo cache: recorded real chat streams, replayed in demo mode (06: ``demo: true``, spec 16).

``record`` runs a question through the real orchestrator once and stores every event as it was
sent. ``replay`` yields them back with the original pacing compressed (tokens are not delayed).
Nothing is ever edited by hand: a question with no recording is an error in demo mode, not a
made-up answer. Files live in ``data/demo_cache/<ipo_id>/<key>.json`` (not committed: they hold
model output; record them with ``uv run poe record-demo``).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Iterator
from pathlib import Path

from pydantic import BaseModel

from finsight.api.events import EVENT_MODELS

Event = tuple[str, BaseModel]


def question_key(ipo_id: str, question: str, language: str) -> str:
    """Stable file name: case, spacing and trailing punctuation do not change the key."""
    q = unicodedata.normalize("NFC", question).casefold()
    q = re.sub(r"[\s?!.।]+", " ", q).strip()
    return hashlib.sha1(f"{ipo_id}|{language}|{q}".encode()).hexdigest()[:16]


class DemoCache:
    """Recorded real chat streams, one JSON file per IPO, question and language."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, ipo_id: str, question: str, language: str) -> Path:
        return self.root / ipo_id / f"{question_key(ipo_id, question, language)}.json"

    def has(self, ipo_id: str, question: str, language: str) -> bool:
        """Whether a recording exists for this question."""
        return self._path(ipo_id, question, language).exists()

    def record(self, ipo_id: str, question: str, language: str, events: Iterable[Event]) -> Path:
        """Store the events of one real run. A run that ended in an error is not stored."""
        rows = [{"event": name, "data": ev.model_dump(mode="json")} for name, ev in events]
        if not rows or rows[-1]["event"] != "final":
            raise ValueError("not recording a stream that did not end with a final event")
        path = self._path(ipo_id, question, language)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"ipo_id": ipo_id, "question": question, "language": language, "events": rows}
        path.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return path

    def replay(self, ipo_id: str, question: str, language: str) -> Iterator[Event]:
        """Yield the recorded events in their original order."""
        path = self._path(ipo_id, question, language)
        for row in json.loads(path.read_text(encoding="utf-8"))["events"]:
            yield row["event"], EVENT_MODELS[row["event"]].model_validate(row["data"])

    def recorded(self, ipo_id: str) -> list[str]:
        """The questions recorded for an IPO (for the recorder's report)."""
        folder = self.root / ipo_id
        if not folder.exists():
            return []
        return [
            json.loads(p.read_text(encoding="utf-8"))["question"]
            for p in sorted(folder.glob("*.json"))
        ]
