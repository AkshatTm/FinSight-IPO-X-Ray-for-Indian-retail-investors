"""Start a job in-process: a background thread on the API machine (B02 §10, B-ADR-16)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol


class Launcher(Protocol):
    """Starts the worker for an uploaded document."""

    def launch(self, doc_id: str, job_id: str) -> None:
        """Start processing ``doc_id`` as job ``job_id``; raise ``LaunchError`` on failure."""


class LaunchError(RuntimeError):
    """The worker could not be started."""


class InlineLauncher:
    """Runs ``work(doc_id, job_id)`` in a background thread (or right away when ``sync``)."""

    def __init__(self, work: Callable[[str, str], object], sync: bool = False) -> None:
        self.work = work
        self.sync = sync

    def launch(self, doc_id: str, job_id: str) -> None:
        """Run the work now (``sync``) or on a background thread."""
        if self.sync:
            self.work(doc_id, job_id)
            return
        threading.Thread(target=self.work, args=(doc_id, job_id), daemon=True).start()
