"""B1.2: local and GCS storage behind one protocol (GCS through a fake client)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from finsight.core.config import load_settings
from finsight.storage import (
    GCSStorage,
    LocalStorage,
    Storage,
    doc_key,
    get_json,
    make_storage,
    put_json,
)


class _FakeBlob:
    def __init__(self, store: dict[str, bytes], name: str) -> None:
        self.store, self.name = store, name
        self.signed: dict[str, Any] = {}

    def upload_from_string(self, data: bytes, content_type: str) -> None:
        self.store[self.name] = data

    def download_as_bytes(self) -> bytes:
        return self.store[self.name]

    def exists(self) -> bool:
        return self.name in self.store

    @property
    def size(self) -> int:
        return len(self.store[self.name])

    def delete(self) -> None:
        del self.store[self.name]

    def generate_signed_url(self, **kwargs: Any) -> str:
        assert kwargs["version"] == "v4"
        return f"https://storage.googleapis.com/b/{self.name}?X-Goog-Signature=fake&m={kwargs['method']}"


class _FakeBucket:
    def __init__(self, store: dict[str, bytes]) -> None:
        self.store = store

    def blob(self, name: str) -> _FakeBlob:
        return _FakeBlob(self.store, name)

    def get_blob(self, name: str) -> _FakeBlob | None:
        return _FakeBlob(self.store, name) if name in self.store else None


class FakeGcsClient:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def bucket(self, name: str) -> _FakeBucket:
        return _FakeBucket(self.store)

    def list_blobs(self, bucket: str, prefix: str) -> list[_FakeBlob]:
        return [_FakeBlob(self.store, n) for n in self.store if n.startswith(prefix)]


@pytest.fixture(params=["local", "gcs"])
def storage(request: pytest.FixtureRequest, tmp_path: Path) -> Storage:
    if request.param == "local":
        return LocalStorage(tmp_path / "store")
    return GCSStorage("finsight-test", client=FakeGcsClient())


def test_round_trip_list_and_delete(storage: Storage) -> None:
    put_json(storage, doc_key("doc_a", "report.json"), {"x": 1})
    storage.put_bytes(doc_key("doc_a", "pages/1.webp"), b"img")
    storage.put_bytes(doc_key("doc_b", "source.pdf"), b"%PDF")
    assert get_json(storage, "docs/doc_a/report.json") == {"x": 1}
    assert storage.list("docs/doc_a/") == ["docs/doc_a/pages/1.webp", "docs/doc_a/report.json"]
    assert storage.exists("docs/doc_b/source.pdf")
    assert storage.delete_prefix("docs/doc_a/") == 2
    assert storage.list("docs/doc_a/") == []
    assert storage.exists("docs/doc_b/source.pdf")


def test_missing_key_is_a_key_error(storage: Storage) -> None:
    with pytest.raises(KeyError):
        storage.get_bytes("docs/none/report.json")
    with pytest.raises(KeyError):
        storage.size("docs/none/report.json")


def test_size_reads_metadata_only(storage: Storage) -> None:
    storage.put_bytes(doc_key("doc_a", "source.pdf"), b"%PDF-1.7 x")
    assert storage.size("docs/doc_a/source.pdf") == 10


@pytest.mark.parametrize("bad", ["", "/etc/passwd", "docs/../x", "docs\\x"])
def test_bad_keys_are_rejected(storage: Storage, bad: str) -> None:
    with pytest.raises(ValueError, match="key"):
        storage.put_bytes(bad, b"x")


def test_gcs_signed_upload_is_a_v4_put() -> None:
    url = GCSStorage("b", client=FakeGcsClient()).signed_upload_url(
        "docs/doc_a/source.pdf", "application/pdf", 900
    )
    assert url.method == "PUT"
    assert "X-Goog-Signature" in url.url
    assert url.expires_at - datetime.now(UTC) <= timedelta(seconds=900)


def test_local_upload_url_goes_through_the_api(tmp_path: Path) -> None:
    url = LocalStorage(tmp_path).signed_upload_url("docs/doc_a/source.pdf", "application/pdf", 60)
    assert (url.url, url.method) == ("/api/uploads/doc_a/file", "POST")


def test_make_storage_follows_the_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(make_storage(load_settings("dev_light")), LocalStorage)
    monkeypatch.setenv("FINSIGHT_STORAGE__BUCKET", "finsight-docs-x")
    gcs = make_storage(load_settings("cloud"), client=FakeGcsClient())
    assert isinstance(gcs, GCSStorage)
    assert gcs.bucket_name == "finsight-docs-x"


def test_gcs_without_bucket_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FINSIGHT_STORAGE__BUCKET", raising=False)
    with pytest.raises(ValueError, match="BUCKET"):
        make_storage(load_settings("cloud"), client=FakeGcsClient())
