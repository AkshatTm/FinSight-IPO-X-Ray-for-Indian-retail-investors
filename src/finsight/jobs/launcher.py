"""Start a job: in-process for the laptop (``jobs.runner: inline``) or as a Cloud Run Job.

The Cloud Run launcher is wired in B3.3a (it calls the Run Admin API with a ``DOC_ID``
override); until then the cloud profiles fail loudly instead of silently doing nothing.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol


class Launcher(Protocol):
    def launch(self, doc_id: str, job_id: str) -> None: ...


class InlineLauncher:
    """Runs ``work(doc_id, job_id)`` in a background thread (or right away when ``sync``)."""

    def __init__(self, work: Callable[[str, str], object], sync: bool = False) -> None:
        self.work = work
        self.sync = sync

    def launch(self, doc_id: str, job_id: str) -> None:
        if self.sync:
            self.work(doc_id, job_id)
            return
        threading.Thread(target=self.work, args=(doc_id, job_id), daemon=True).start()


class CloudRunLauncher:
    """Placeholder until B3.3a: Cloud Run Jobs execution with a ``DOC_ID`` override."""

    def launch(self, doc_id: str, job_id: str) -> None:
        raise NotImplementedError("Cloud Run job launch arrives in B3.3a (no deploy yet)")
