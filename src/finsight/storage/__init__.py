"""Document artefact storage: the local ``data/store`` tree or a GCS bucket behind one protocol."""

from __future__ import annotations

from typing import Any

from finsight.core.config import Settings
from finsight.storage.base import SignedUrl, Storage, doc_key, get_json, put_json
from finsight.storage.gcs import GCSStorage
from finsight.storage.local import LocalStorage


def make_storage(settings: Settings, client: Any | None = None) -> Storage:
    """The storage the profile asks for (``storage.backend``)."""
    cfg = settings.storage
    if cfg.backend == "gcs":
        if not cfg.bucket:
            raise ValueError("storage.backend is gcs but FINSIGHT_STORAGE__BUCKET is not set")
        return GCSStorage(cfg.bucket, client=client)
    root = cfg.local_dir if cfg.local_dir.is_absolute() else settings.root / cfg.local_dir
    return LocalStorage(root)


__all__ = [
    "GCSStorage",
    "LocalStorage",
    "SignedUrl",
    "Storage",
    "doc_key",
    "get_json",
    "make_storage",
    "put_json",
]
