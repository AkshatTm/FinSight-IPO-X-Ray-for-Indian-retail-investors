import hashlib
import re

import pytest

from finsight.core.config import get_settings
from finsight.ingest.registry import get_demo_ipo, list_demo_ipos

DEV = {"hexaware-technologies-2025", "ather-energy-2025", "urban-company-2025"}


def test_ten_demo_ipos_with_unique_slug_ids() -> None:
    ipos = list_demo_ipos()
    ids = [i.ipo_id for i in ipos]
    assert len(ids) == 10
    assert len(set(ids)) == 10
    assert all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*-20\d\d", i) for i in ids)


def test_split_is_three_dev_seven_test_and_matches_the_adr() -> None:
    ipos = list_demo_ipos()
    assert {i.ipo_id for i in ipos if i.split == "dev"} == DEV
    assert sum(i.split == "test" for i in ipos) == 7


def test_every_ipo_has_both_documents_with_valid_checksums() -> None:
    for ipo in list_demo_ipos():
        for doc in (ipo.rhp, ipo.prospectus):
            assert re.fullmatch(r"[0-9a-f]{64}", doc.sha256), ipo.ipo_id
            assert doc.pages > 100, ipo.ipo_id
            assert doc.file.suffix == ".pdf"
        assert ipo.rhp.sha256 != ipo.prospectus.sha256, f"{ipo.ipo_id}: same file twice?"


def test_document_paths_follow_the_storage_layout() -> None:
    for ipo in list_demo_ipos():
        assert ipo.rhp.file.as_posix().endswith(f"data/raw/rhp/{ipo.ipo_id}.pdf")
        assert ipo.prospectus.file.as_posix().endswith(f"data/raw/prospectus/{ipo.ipo_id}.pdf")


def test_get_demo_ipo_and_unknown_id() -> None:
    assert get_demo_ipo("meesho-2025").company == "Meesho Limited"
    with pytest.raises(KeyError, match="meesho-2025"):
        get_demo_ipo("nope-2025")


def test_paths_are_resolved_against_the_repo_root() -> None:
    ipo = get_demo_ipo("meesho-2025")
    assert ipo.rhp.file.is_absolute()
    assert ipo.rhp.file == get_settings().root / "data" / "raw" / "rhp" / "meesho-2025.pdf"


@pytest.mark.slow
def test_local_pdfs_match_the_recorded_checksums() -> None:
    for ipo in list_demo_ipos():
        for doc in (ipo.rhp, ipo.prospectus):
            if not doc.file.exists():
                pytest.skip("demo PDFs are not on this machine")
            assert hashlib.sha256(doc.file.read_bytes()).hexdigest() == doc.sha256, doc.file.name


def test_showcase_doc_ids_follow_the_sha256() -> None:
    from finsight.core.ids import make_doc_id

    for ipo in list_demo_ipos():
        for doc in (ipo.rhp, ipo.prospectus):
            assert doc.doc_id == make_doc_id(doc.sha256)
        assert ipo.primary_doc_id != ipo.companion_doc_id
