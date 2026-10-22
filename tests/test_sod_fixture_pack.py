"""SOD fixture pack (P4 AR-02 / CC-05): Summary of the Offer Document word boxes for 10 RHPs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from real import loader

ROOT = Path(__file__).resolve().parent.parent
SOD_IDS = [
    "jio-platforms-2026",
    "hyundai-motor-india-2024",
    "bajaj-housing-finance-2024",
    "emcure-pharmaceuticals-2024",
    "premier-energies-2024",
    "kronox-lab-sciences-2024",
    "national-securities-depository-2025",
    "anthem-biosciences-2025",
    "jsw-cement-2025",
    "anlon-healthcare-2025",
]
DISCLOSED_EXCEPTION = "jio-platforms-2026"  # test-informed parser diagnosis only (P4_PLAN §2)
pytestmark = pytest.mark.skipif(not loader.SOD.exists(), reason="SOD fixtures not exported")


def test_all_ten_exported_and_indexed() -> None:
    assert loader.ipo_ids(loader.SOD) == sorted(SOD_IDS)
    index = json.loads((loader.SOD / "index.json").read_text(encoding="utf-8"))
    assert sorted(r["ipo_id"] for r in index) == sorted(SOD_IDS)


def test_only_jio_is_excluded_and_the_rest_are_train_or_dev() -> None:
    data = ROOT / "ml" / "handoff" / "data"
    excluded = json.loads((data / "excluded_ipos.json").read_text(encoding="utf-8"))["ipos"]
    slices = {
        r["ipo_id"]: r["slice"]
        for r in json.loads((data / "splits_by_ipo.json").read_text(encoding="utf-8"))["ipos"]
    }
    assert [i for i in SOD_IDS if i in excluded] == [DISCLOSED_EXCEPTION]
    assert all(slices[i] in {"train", "dev"} for i in SOD_IDS if i != DISCLOSED_EXCEPTION)


@pytest.mark.parametrize("ipo_id", SOD_IDS)
def test_sod_pages_load_with_words_and_tables(ipo_id: str) -> None:
    doc = loader.load_doc(ipo_id, root=loader.SOD)
    kept = loader.kept_pages(ipo_id, root=loader.SOD)
    assert list(kept) == ["summary"]
    assert [p.number for p in doc.pages] == kept["summary"]
    assert len(doc.pages) >= 5
    assert all(p.words for p in doc.pages)
    assert doc.n_pages > len(doc.pages)  # a slice of the RHP, not the document
    assert loader.load_sections(ipo_id, root=loader.SOD)
    assert loader.load_tables(ipo_id, root=loader.SOD)
    source = loader.raw(ipo_id, root=loader.SOD)["sod_source"]
    # Jio's RHP has no SOD heading: its Introduction (The Issue + summary_*) is exported instead.
    expected = "introduction_run" if ipo_id == DISCLOSED_EXCEPTION else "sod_section"
    assert source.startswith(expected)
