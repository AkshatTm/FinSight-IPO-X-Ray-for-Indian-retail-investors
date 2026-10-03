"""End-to-end smoke test of a running FinSight API (B3.3a; used in B2.7 / B3.3b and in CI).

    uv run python scripts/cloud_smoke.py --base-url https://<api> --pdf <offer document>.pdf
    uv run python scripts/cloud_smoke.py --base-url http://localhost:8080 --synthetic

Steps: health → upload limits → upload (init → file to the signed URL or the local route →
complete) → wait until the document is ready, partial or failed → report. Prints one JSON summary
with each step's time; ``--out`` also writes it (e.g. ``eval_results/b/smoke_deploy.json``).
Exit code 0 only when every step passed.

A signed-in call needs a Supabase access token: put it in an environment variable and name that
variable with ``--token-env`` (default ``FINSIGHT_SMOKE_TOKEN``). The token is never printed.
Only the standard library is used, so the script runs anywhere Python 3.11 does.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

FINAL = {"ready", "partial", "failed"}


@dataclass
class Response:
    status: int
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body or b"null")


class Http(Protocol):
    def __call__(
        self, method: str, url: str, body: bytes | None, headers: dict[str, str]
    ) -> Response: ...


def urllib_http(method: str, url: str, body: bytes | None, headers: dict[str, str]) -> Response:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return Response(resp.status, resp.read())
    except urllib.error.HTTPError as err:
        return Response(err.code, err.read())


@dataclass
class Smoke:
    base_url: str
    http: Http = urllib_http
    token: str | None = None
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    steps: list[dict[str, Any]] = field(default_factory=list)

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json", **(extra or {})}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def call(
        self, method: str, path: str, body: Any = None, raw: bytes | None = None, **headers: str
    ) -> Response:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        extra = dict(headers)
        if body is not None:
            extra["Content-Type"] = "application/json"
        return self.http(method, self.base_url.rstrip("/") + path, data, self._headers(extra))

    def step(self, name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any] | None:
        t0 = self.clock()
        try:
            detail = fn()
            ok = True
        except SmokeFailed as err:
            detail, ok = {"error": str(err)}, False
        self.steps.append(
            {"step": name, "ok": ok, "seconds": round(self.clock() - t0, 2), **detail}
        )
        return detail if ok else None

    # ------------------------------------------------------------------ steps
    def health(self) -> dict[str, Any]:
        resp = self.call("GET", "/api/health")
        _expect(resp, 200, "health")
        return {"status": resp.status}

    def limits(self) -> dict[str, Any]:
        resp = self.call("GET", "/api/uploads/limits")
        _expect(resp, 200, "limits")
        return {"limits": resp.json()}

    def upload(self, pdf: bytes, filename: str) -> dict[str, Any]:
        sha = hashlib.sha256(pdf).hexdigest()
        init = self.call(
            "POST",
            "/api/uploads/init",
            {"filename": filename, "size_bytes": len(pdf), "sha256": sha},
        )
        _expect(init, 200, "init")
        started = init.json()
        if started["status"] == "exists":
            return {"doc_id": started["doc_id"], "exists": True}
        url = str(started["upload_url"])
        if url.startswith(("http://", "https://")):  # a signed GCS URL: no API token on it
            sent = self.http(
                started.get("upload_method", "PUT"), url, pdf, {"Content-Type": "application/pdf"}
            )
        else:
            sent = self.call("POST", url, raw=pdf, **{"Content-Type": "application/pdf"})
        if sent.status not in (200, 201):
            raise SmokeFailed(f"file upload returned {sent.status}")
        done = self.call("POST", f"/api/uploads/{started['doc_id']}/complete")
        _expect(done, 200, "complete")
        return {"doc_id": started["doc_id"], "job_id": done.json()["job_id"], "exists": False}

    def wait(self, doc_id: str, timeout_s: float, every_s: float = 5.0) -> dict[str, Any]:
        t0 = self.clock()
        while True:
            resp = self.call("GET", f"/api/docs/{doc_id}")
            _expect(resp, 200, "status")
            detail = resp.json()
            status = detail["doc"]["status"]
            if status in FINAL:
                stages = {s["stage"]: s["status"] for s in detail.get("stages", [])}
                if status == "failed":
                    raise SmokeFailed(f"document failed; stages {stages}")
                return {"status": status, "stages": stages}
            if self.clock() - t0 > timeout_s:
                raise SmokeFailed(f"still {status} after {timeout_s:.0f} s")
            self.sleep(every_s)

    def report(self, doc_id: str) -> dict[str, Any]:
        resp = self.call("GET", f"/api/docs/{doc_id}/report")
        _expect(resp, 200, "report")
        return {"report_bytes": len(resp.body)}

    def run(self, pdf: bytes | None, filename: str, timeout_s: float) -> dict[str, Any]:
        self.step("health", self.health)
        self.step("limits", self.limits)
        if pdf is not None:
            up = self.step("upload", lambda: self.upload(pdf, filename))
            if up is not None:
                doc_id = str(up["doc_id"])
                if self.step("process", lambda: self.wait(doc_id, timeout_s)) is not None:
                    self.step("report", lambda: self.report(doc_id))
        return {
            "base_url": self.base_url,
            "ok": all(s["ok"] for s in self.steps),
            "steps": self.steps,
        }


class SmokeFailed(RuntimeError):
    pass


def _expect(resp: Response, status: int, what: str) -> None:
    if resp.status != status:
        code = ""
        with contextlib.suppress(ValueError, AttributeError):
            code = str(resp.json().get("error", {}).get("code", ""))
        raise SmokeFailed(f"{what} returned {resp.status} {code}".strip())


def synthetic_pdf() -> bytes:
    """A small synthetic RHP from the test fixtures (needs PyMuPDF: ``uv sync``)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "fixtures"))
    import tempfile

    from make_fixture_pdf import build_offer_pdf

    with tempfile.TemporaryDirectory() as tmp:
        return build_offer_pdf(Path(tmp) / "smoke.pdf", "rhp").read_bytes()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cloud_smoke.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--base-url", required=True)
    src = p.add_mutually_exclusive_group()
    src.add_argument("--pdf", type=Path, help="an offer document to upload")
    src.add_argument("--synthetic", action="store_true", help="upload a small synthetic RHP")
    p.add_argument("--token-env", default="FINSIGHT_SMOKE_TOKEN")
    p.add_argument("--timeout", type=float, default=900.0, help="seconds to wait for processing")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    pdf = args.pdf.read_bytes() if args.pdf else (synthetic_pdf() if args.synthetic else None)
    name = args.pdf.name if args.pdf else "smoke.pdf"
    smoke = Smoke(args.base_url, token=os.environ.get(args.token_env) or None)
    summary = smoke.run(pdf, name, args.timeout)
    text = json.dumps(summary, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
