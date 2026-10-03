"""B1.2: local storage behind the ``Storage`` protocol (B-ADR-16 removed GCS)."""

from __future__ import annotations

from pathlib import Path

import pytest

from finsight.core.config import load_settings
from finsight.storage import (
    LocalStorage,
    Storage,
    doc_key,
    get_json,
    make_storage,
    put_json,
)


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    return LocalStorage(tmp_path / "store")


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


def test_local_upload_url_goes_through_the_api(tmp_path: Path) -> None:
    url = LocalStorage(tmp_path).signed_upload_url("docs/doc_a/source.pdf", "application/pdf", 60)
    assert (url.url, url.method) == ("/api/uploads/doc_a/file", "POST")


def test_make_storage_follows_the_profile() -> None:
    assert isinstance(make_storage(load_settings("dev_light")), LocalStorage)
