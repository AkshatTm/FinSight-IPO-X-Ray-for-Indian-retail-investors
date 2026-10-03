"""B1.1a: upload validation and document-type detection on synthetic PDFs."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf
import pytest
from make_fixture_pdf import build_blank_pdf, build_offer_pdf

from finsight.core.config import UploadsConfig, load_settings
from finsight.core.ids import make_doc_id
from finsight.ingest import detect_type, sha256_file, validate_pdf

CASES = [
    ("rhp", "rhp", None),
    ("drhp", "drhp", None),
    ("prospectus", "prospectus", None),
    ("non_offer", None, "not_offer_document"),
    ("news_mention", None, "not_offer_document"),
    ("scanned", None, "scanned"),
    ("password", None, "password"),
]


@pytest.mark.parametrize(("kind", "doc_type", "code"), CASES)
def test_each_synthetic_pdf_gets_its_type_or_code(
    tmp_path: Path, kind: str, doc_type: str | None, code: str | None
) -> None:
    check = validate_pdf(build_offer_pdf(tmp_path / f"{kind}.pdf", kind))
    assert check.doc_type == doc_type
    assert check.code == code
    assert check.ok is (code is None)


def test_prospectus_mentioning_the_rhp_in_its_body_is_a_prospectus(tmp_path: Path) -> None:
    with pymupdf.open(build_offer_pdf(tmp_path / "p.pdf", "prospectus")) as doc:
        assert detect_type(doc) == "prospectus"


def test_not_a_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "x.pdf"
    path.write_bytes(b"hello, not a pdf")
    assert validate_pdf(path).code == "not_offer_document"


def test_size_edge_at_the_limit(tmp_path: Path) -> None:
    limits = UploadsConfig(max_mb=1)
    at = tmp_path / "at.bin"
    at.write_bytes(b"\0" * (1024 * 1024))
    over = tmp_path / "over.bin"
    over.write_bytes(b"\0" * (1024 * 1024 + 1))
    assert validate_pdf(at, limits).code != "too_large"
    assert validate_pdf(over, limits).code == "too_large"


def test_default_limit_is_50_mb(tmp_path: Path) -> None:
    over = tmp_path / "big.bin"
    with over.open("wb") as handle:  # sparse file: cheap even at 50 MB
        handle.truncate(50 * 1024 * 1024 + 1)
    assert validate_pdf(over).code == "too_large"
    assert load_settings("dev_light").uploads.max_mb == 50


@pytest.mark.parametrize(("pages", "too_many"), [(1500, False), (1501, True)])
def test_page_edge_at_1500(tmp_path: Path, pages: int, too_many: bool) -> None:
    check = validate_pdf(build_blank_pdf(tmp_path / f"{pages}.pdf", pages))
    assert (check.code == "too_many_pages") is too_many
    assert check.pages == pages


def test_same_bytes_same_doc_id(tmp_path: Path) -> None:
    a = build_offer_pdf(tmp_path / "a.pdf", "rhp")
    b = tmp_path / "copy.pdf"
    b.write_bytes(a.read_bytes())
    assert validate_pdf(a).doc_id == validate_pdf(b).doc_id == make_doc_id(sha256_file(a))


def test_sha256_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "f.bin"
    path.write_bytes(b"abc" * 1_000_000)
    assert sha256_file(path, chunk=4096) == hashlib.sha256(path.read_bytes()).hexdigest()


def test_limits_come_from_config_yaml() -> None:
    uploads = load_settings("cloud").uploads
    assert (uploads.max_mb, uploads.max_pages) == (50, 1500)
    assert uploads.scanned_min_median_chars == 100
