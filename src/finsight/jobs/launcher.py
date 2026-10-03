"""Start a job: in-process for the laptop (``jobs.runner: inline``) or as a Cloud Run Job.

On Cloud Run the API starts one execution of the worker job per document through the Run Admin
API v2 (``jobs.run`` with a ``DOC_ID``/``JOB_ID`` env override, B02 §10). The access token comes
from the metadata server of the API's service account, which needs ``roles/run.invoker`` on the
job (``deploy/gcp/IAM.md``). Only the standard library is used, so the API image stays small.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

RUN_API = "https://run.googleapis.com/v2"
METADATA_TOKEN = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)
TIMEOUT_S = 10.0


class Launcher(Protocol):
    """Starts the worker for an uploaded document."""

    def launch(self, doc_id: str, job_id: str) -> None:
        """Start processing ``doc_id`` as job ``job_id``; raise ``LaunchError`` on failure."""


class LaunchError(RuntimeError):
    """The worker job could not be started (no credentials, API error, network)."""


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


TokenSource = Callable[[], str]
Post = Callable[[str, dict[str, Any], str], dict[str, Any]]


def metadata_token() -> str:
    """An OAuth access token for the service account the container runs as."""
    req = urllib.request.Request(METADATA_TOKEN, headers={"Metadata-Flavor": "Google"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return str(json.load(resp)["access_token"])
    except (urllib.error.URLError, KeyError, ValueError) as err:
        raise LaunchError(f"no access token from the metadata server: {err}") from err


def post_json(url: str, body: dict[str, Any], token: str) -> dict[str, Any]:
    """POST JSON with a bearer token; any HTTP or network error is a ``LaunchError``."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return dict(json.load(resp))
    except urllib.error.HTTPError as err:
        detail = err.read()[:300].decode("utf-8", "replace")
        raise LaunchError(f"Cloud Run returned {err.code}: {detail}") from err
    except urllib.error.URLError as err:
        raise LaunchError(f"Cloud Run unreachable: {err.reason}") from err


def run_job_request(doc_id: str, job_id: str) -> dict[str, Any]:
    """The ``jobs.run`` body: one task, the document and job ids as env overrides."""
    env = [{"name": "DOC_ID", "value": doc_id}, {"name": "JOB_ID", "value": job_id}]
    return {"overrides": {"containerOverrides": [{"env": env}], "taskCount": 1}}


class CloudRunLauncher:
    """Starts one execution of a Cloud Run Job per document (returns once it is accepted)."""

    def __init__(
        self,
        project: str,
        region: str,
        job: str,
        *,
        token: TokenSource = metadata_token,
        post: Post = post_json,
    ) -> None:
        self.project, self.region, self.job = project, region, job
        self.token, self.post = token, post

    @property
    def url(self) -> str:
        """The Run Admin API v2 ``jobs/{job}:run`` endpoint."""
        return f"{RUN_API}/projects/{self.project}/locations/{self.region}/jobs/{self.job}:run"

    def launch(self, doc_id: str, job_id: str) -> None:
        """Run the Cloud Run job with ``DOC_ID`` and ``JOB_ID`` overrides."""
        if not self.project:
            raise LaunchError("GCP_PROJECT is not set")
        self.post(self.url, run_job_request(doc_id, job_id), self.token())


def cloud_run_launcher(job: str, environ: dict[str, str] | None = None) -> CloudRunLauncher:
    """A launcher for ``job`` in ``GCP_PROJECT`` / ``GCP_REGION`` (default asia-southeast1)."""
    env = dict(os.environ) if environ is None else environ
    return CloudRunLauncher(
        env.get("GCP_PROJECT", ""), env.get("GCP_REGION") or "asia-southeast1", job
    )
