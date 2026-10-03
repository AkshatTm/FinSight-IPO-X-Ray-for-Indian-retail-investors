"""The ``Storage`` protocol: bytes under keys like ``docs/<doc_id>/report.json`` (B02 §9)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SignedUrl:
    """Where the browser sends a file, and until when the link works."""

    url: str
    method: str
    expires_at: datetime


@runtime_checkable
class Storage(Protocol):
    """Document artefacts by key. Keys use ``/``; no leading slash; never ``..``."""

    def put_bytes(self, key: str, data: bytes, content_type: str = ...) -> None:
        """Write ``data`` under ``key``, replacing any existing object."""

    def get_bytes(self, key: str) -> bytes:
        """Read the object under ``key``; raise ``KeyError`` if there is none."""

    def exists(self, key: str) -> bool:
        """Whether an object exists under ``key``."""

    def list(self, prefix: str) -> list[str]:
        """Every key under ``prefix``, sorted."""

    def delete_prefix(self, prefix: str) -> int:
        """Delete every object under ``prefix`` and return how many there were."""

    def signed_upload_url(self, key: str, content_type: str, ttl_s: int) -> SignedUrl:
        """A short-lived link the browser uploads the file to."""


def check_key(key: str) -> str:
    """Reject keys that could escape the storage root."""
    if not key or key.startswith("/") or "\\" in key or ".." in key.split("/"):
        raise ValueError(f"bad storage key {key!r}")
    return key


def doc_key(doc_id: str, name: str) -> str:
    """``docs/<doc_id>/<name>``: the layout every stage writes to."""
    return check_key(f"docs/{doc_id}/{name}")


def put_json(storage: Storage, key: str, value: Any) -> None:
    """Write ``value`` as UTF-8 JSON (dates and decimals as strings)."""
    data = json.dumps(value, ensure_ascii=False, indent=1, default=str).encode("utf-8")
    storage.put_bytes(key, data, "application/json")


def get_json(storage: Storage, key: str) -> Any:
    """Read a JSON object written by :func:`put_json`."""
    return json.loads(storage.get_bytes(key).decode("utf-8"))
