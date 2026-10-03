"""The real-section fixture pack (B0.4, B-ADR-15): shape, size, and red-flag source coverage."""

from __future__ import annotations

from pathlib import Path

import pytest
from real import loader

PACK = Path(loader.ROOT)
pytestmark = pytest.mark.skipif(not loader.ipo_ids(), reason="fixture pack not exported")


def test_size_limits_and_no_pdfs_or_weights() -> None:
    files = [p for p in PACK.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    assert not [
        p for p in files if p.suffix.lower() in {".pdf", ".bin", ".safetensors", ".gguf", ".onnx"}
    ]
    assert all(p.stat().st_size <= 5 * 1024 * 1024 for p in files)
    total = sum(p.stat().st_size for p in files) / 1e6
    print(f"fixture pack: {len(files)} files, {total:.2f} MB")
    assert total <= 20 * 1.048576


def test_ten_ipos_with_rhp_and_prospectus() -> None:
    ids = loader.ipo_ids()
    assert len(ids) == 10
    for ipo in ids:
        assert (PACK / ipo / "prospectus.pages.json.gz").exists()


def test_pages_have_words_and_boxes() -> None:
    ipo = loader.ipo_ids()[0]
    doc = loader.load_doc(ipo)
    assert doc.pages
    assert doc.n_pages >= len(doc.pages)
    page = doc.pages[len(doc.pages) // 2]
    assert page.words
    assert page.text
    w = page.words[0]
    assert w.bbox[2] >= w.bbox[0]
    assert w.font_size > 0
    assert all(p.number <= doc.n_pages for p in doc.pages)


def test_sections_and_kept_pages_agree() -> None:
    for ipo in loader.ipo_ids():
        doc = loader.load_doc(ipo)
        have = {p.number for p in doc.pages}
        for label, pages in loader.kept_pages(ipo).items():
            assert set(pages) <= have, (ipo, label)
        ids = {s.id for s in loader.load_sections(ipo)}
        assert {"cover", "risk_factors", "capital_structure"} <= ids, ipo


def test_tables_load() -> None:
    tables = [t for ipo in loader.ipo_ids() for t in loader.load_tables(ipo)]
    assert tables
    assert all(t.cells for t in tables)


def test_every_red_flag_has_sources_for_most_ipos() -> None:
    coverage = loader.rf_coverage()
    gaps = {rf: sorted(set(loader.ipo_ids()) - set(ipos)) for rf, ipos in coverage.items()}
    print("red-flag source gaps:", {rf: g for rf, g in gaps.items() if g})
    for rf, ipos in coverage.items():
        assert len(ipos) >= 8, f"{rf}: only {len(ipos)}/10 IPOs have source pages"


def test_corpus_excerpts_and_samples() -> None:
    texts = loader.corpus_risk_factors()
    assert len(texts) == 20
    years = {k[-4:] for k in texts}
    assert len(years) >= 8, "stratified by year"
    assert all(len(t) > 2000 for t in texts.values())
    assert loader.corpus_stats()
    risks = loader.fake_risks()
    assert len(risks) == 20
    assert {r["label_source"] for r in risks} == {"synthetic"}
    assert len(list((PACK / "samples").glob("parsed_*.json.gz"))) == 2
