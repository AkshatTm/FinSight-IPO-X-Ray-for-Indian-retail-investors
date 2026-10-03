"""Files under a local directory (laptop profiles and tests)."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from finsight.storage.base import SignedUrl, check_key


class LocalStorage:
    """``Storage`` on disk. Uploads go through the API (``POST /api/uploads/{doc_id}/file``)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        """The file that holds ``key`` (after checking the key)."""
        return self.root / check_key(key)

    def put_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        """Write atomically through a temporary file."""
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)  # readers never see a half-written file

    def get_bytes(self, key: str) -> bytes:
        """Read the file; ``KeyError`` if it does not exist."""
        try:
            return self.path(key).read_bytes()
        except FileNotFoundError:
            raise KeyError(key) from None

    def size(self, key: str) -> int:
        """The file's size from ``stat``; ``KeyError`` if it does not exist."""
        try:
            return self.path(key).stat().st_size
        except FileNotFoundError:
            raise KeyError(key) from None

    def exists(self, key: str) -> bool:
        """Whether the file exists."""
        return self.path(key).is_file()

    def list(self, prefix: str) -> list[str]:
        """Every file under ``prefix`` as a sorted list of keys."""
        base = self.root / prefix if prefix else self.root
        if not base.exists():
            return []
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        return sorted(p.relative_to(self.root).as_posix() for p in files)

    def delete_prefix(self, prefix: str) -> int:
        """Remove the folder or file under ``prefix``; return the files removed."""
        check_key(prefix.rstrip("/"))
        keys = self.list(prefix)
        target = self.root / prefix
        if target.is_dir():
            shutil.rmtree(target)
        elif target.is_file():
            target.unlink()
        return len(keys)

    def signed_upload_url(self, key: str, content_type: str, ttl_s: int) -> SignedUrl:
        """The API's own upload route (there is no signed URL on disk)."""
        doc_id = check_key(key).split("/")[1]
        return SignedUrl(
            url=f"/api/uploads/{doc_id}/file",
            method="POST",
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_s),
        )
