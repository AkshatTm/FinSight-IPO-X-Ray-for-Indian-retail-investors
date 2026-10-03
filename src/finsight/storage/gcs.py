"""Google Cloud Storage with V4 signed URLs (B-ADR-04, B02 §9).

The ``google-cloud-storage`` client lives in the optional ``cloud`` dependency group; tests pass
a fake client with the same small surface (``bucket().blob()``, ``list_blobs``). On Cloud Run the
runtime service account signs through IAM ``signBlob``, so it needs Token Creator on itself.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from typing import Any

from finsight.storage.base import SignedUrl, check_key


class GCSStorage:
    """``Storage`` on one private GCS bucket."""

    def __init__(self, bucket: str, client: Any | None = None) -> None:
        if client is None:  # pragma: no cover - needs the cloud group and credentials
            # imported by name: the package is optional and untyped (no mypy stubs)
            gcs: Any = importlib.import_module("google.cloud.storage")

            client = gcs.Client()
        self.client = client
        self.bucket_name = bucket
        self.bucket = client.bucket(bucket)

    def put_bytes(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        self.bucket.blob(check_key(key)).upload_from_string(data, content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        blob = self.bucket.blob(check_key(key))
        if not blob.exists():
            raise KeyError(key)
        data: bytes = blob.download_as_bytes()
        return data

    def exists(self, key: str) -> bool:
        return bool(self.bucket.blob(check_key(key)).exists())

    def list(self, prefix: str) -> list[str]:
        return sorted(blob.name for blob in self.client.list_blobs(self.bucket_name, prefix=prefix))

    def delete_prefix(self, prefix: str) -> int:
        check_key(prefix.rstrip("/"))
        names = self.list(prefix)
        for name in names:
            self.bucket.blob(name).delete()
        return len(names)

    def signed_upload_url(self, key: str, content_type: str, ttl_s: int) -> SignedUrl:
        expires = timedelta(seconds=ttl_s)
        url = self.bucket.blob(check_key(key)).generate_signed_url(
            version="v4", expiration=expires, method="PUT", content_type=content_type
        )
        return SignedUrl(url=url, method="PUT", expires_at=datetime.now(UTC) + expires)
