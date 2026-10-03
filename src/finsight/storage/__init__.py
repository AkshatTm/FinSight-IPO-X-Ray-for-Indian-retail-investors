"""Document artefact storage: the local ``data/store`` tree behind one protocol."""

from __future__ import annotations

from finsight.core.config import Settings
from finsight.storage.base import SignedUrl, Storage, doc_key, get_json, put_json
from finsight.storage.local import LocalStorage


def make_storage(settings: Settings) -> Storage:
    """The storage the profile asks for (``storage.backend``)."""
    cfg = settings.storage
    root = cfg.local_dir if cfg.local_dir.is_absolute() else settings.root / cfg.local_dir
    return LocalStorage(root)


__all__ = [
    "LocalStorage",
    "SignedUrl",
    "Storage",
    "doc_key",
    "get_json",
    "make_storage",
    "put_json",
]
