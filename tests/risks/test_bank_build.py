"""C2.1: golden segmentation on real fixture pages, bank build, window wiring and leakage."""

from datetime import date
from pathlib import Path

import numpy as np
import pytest
from real import loader

from finsight.core.schemas import Risk
from finsight.pipeline import split_risks
from finsight.risks import load_bank, segment_text, to_risks
from finsight.risks.bank_build import (
    build_rows,
    count_by_year,
    segmentation_stats,
    write_parquet,
)
from finsight.splits import (
    Manifest,
    SplitEntry,
    SplitsFile,
    check_manifests,
    reference_bank,
)

# Golden counts: what the segmenter finds on the real Risk Factors pages today (3 dev IPOs).
# A change here must be a deliberate segmentation change, checked against the PDF by hand.
GOLDEN = {
    "ather-energy-2025": (98, "We have received some customer complaints"),
    "hexaware-technologies-2025": (75, "We derived 73.4% and 71.5% of our revenue"),
    "urban-company-2025": (75, "We have incurred net losses and negative operating cash flows"),
}


@pytest.mark.parametrize("ipo", sorted(GOLDEN))
def test_golden_segmentation_on_real_pages(ipo: str) -> None:
    doc = loader.load_doc(ipo)
    risks = split_risks(doc, loader.load_sections(ipo), loader.load_tables(ipo))
    count, first = GOLDEN[ipo]
    assert len(risks) == count
    assert risks[0].title.startswith(first)
    assert [r.order for r in risks] == list(range(1, count + 1))
    assert len({r.rid for r in risks}) == count
    assert all(len(r.title.split()) >= 5 for r in risks)
    assert all(r.body.strip() for r in risks)
    assert all(r.page_start <= r.page_end for r in risks)


def test_corpus_text_segments_most_excerpts() -> None:
    texts = loader.corpus_risk_factors()
    counts = {ipo: len(to_risks(segment_text(t))) for ipo, t in texts.items()}
    assert len(counts) == 20
    # 8 of 20 before the bare-number fix (a number alone on its line), 17 after
    assert sum(1 for n in counts.values() if n >= 10) >= 16


def entry(ipo: str, slice_: str, company: str, day: str | None, year: int | None = None):
    return SplitEntry(
        ipo_id=ipo, company=company, company_key=company.lower(), source="new" if day else "corpus",
        slice=slice_, doc_date=date.fromisoformat(day) if day else None, close_year=year,
    )  # fmt: skip


def splits() -> SplitsFile:
    return SplitsFile(
        ipos=[
            entry("old-2022", "train", "Old Co", None, 2022),
            entry("tr-2024", "train", "Train Co", "2024-06-01"),
            entry("dv-2025", "dev", "Dev Co", "2025-03-01"),
            entry("te-2025", "test", "Test Co", "2025-09-01"),
            entry("gone-2025", "train", "Gone Co", "2025-01-01"),
        ]
    )


def risk(i: int, title: str = "") -> Risk:
    return Risk(
        rid=f"r{i}", order=i, title=title or f"We depend on supplier number {i} heavily here",
        body=f"Body of risk {i}. It has two sentences. And a third.", page_start=1, page_end=1,
    )  # fmt: skip


def fake_source(e: SplitEntry) -> list[Risk] | None:
    return None if e.ipo_id == "gone-2025" else [risk(1), risk(2)]


def fake_embed(texts):
    rng = np.random.default_rng(len(texts))
    return rng.normal(size=(len(texts), 4)).astype(np.float32)


def test_build_partitions_bank_and_eval_and_reports_missing() -> None:
    res = build_rows(splits(), fake_source, fake_embed)
    bank_ids = {r["ipo_id"] for r in res.rows["bank"]}
    eval_ids = {r["ipo_id"] for r in res.rows["eval"]}
    assert bank_ids == {"old-2022", "tr-2024", "dv-2025"}
    assert eval_ids == {"te-2025"}
    assert res.missing == ["gone-2025"]
    assert {r["year"] for r in res.rows["bank"]} == {2022, 2024, 2025}
    assert count_by_year(res.rows["bank"]) == {2022: 2, 2024: 2, 2025: 2}
    assert {r["split"] for r in res.rows["bank"]} == {"train", "dev"}


def test_bank_manifest_passes_and_a_test_ipo_would_leak() -> None:
    res = build_rows(splits(), fake_source, fake_embed)
    ok = Manifest(artefact="risk_bank", kind="train", written_by="t",
                  ipo_ids=sorted({r["ipo_id"] for r in res.rows["bank"]}))  # fmt: skip
    assert check_manifests([ok], splits()) == []
    bad = ok.model_copy(update={"ipo_ids": [*ok.ipo_ids, "te-2025"]})
    assert check_manifests([bad], splits())  # a test IPO in a train artefact is a violation


def test_parquet_roundtrip_and_rolling_window(tmp_path: Path) -> None:
    res = build_rows(splits(), fake_source, fake_embed)
    write_parquet(res.rows["bank"], tmp_path / "risk_bank.parquet")
    write_parquet(res.rows["eval"], tmp_path / "risk_eval.parquet")
    bank = load_bank(tmp_path / "risk_bank.parquet", years=None)
    ev = load_bank(tmp_path / "risk_eval.parquet", years=None)
    assert len(bank) == 6
    assert set(bank.ipo_ids or []) == {"old-2022", "tr-2024", "dv-2025"}
    # eval window for the test IPO (2025-09-01, 4 years): train + dev only, own company excluded
    window = reference_bank(bank, splits(), date(2025, 9, 1), exclude_ipo="te-2025")
    assert set(window.ipo_ids or []) == {"old-2022", "tr-2024", "dv-2025"}
    # a document in early 2024: only the corpus IPO of 2022 is a past IPO (4-year rule)
    early = reference_bank(bank, splits(), date(2024, 2, 1))
    assert set(early.ipo_ids or []) == {"old-2022"}
    # product window adds the test IPOs; concat joins the two parquet files
    product = bank.concat(ev)
    later = reference_bank(product, splits(), date(2026, 1, 1), kind="product")
    assert "te-2025" in (later.ipo_ids or [])
    assert "te-2025" not in (reference_bank(product, splits(), date(2026, 1, 1)).ipo_ids or [])


def test_subset_needs_an_ipo_id_column(tmp_path: Path) -> None:
    from finsight.risks.bank import RiskBank

    legacy = RiskBank(["A"], np.array([2020]), ["t"], np.ones((1, 2), dtype=np.float32))
    with pytest.raises(ValueError, match="ipo_id"):
        legacy.subset({"x"})


def test_segmentation_stats_by_source() -> None:
    sp = splits().by_id()
    stats = segmentation_stats({"old-2022": [risk(1), risk(2)], "tr-2024": [risk(1)]}, sp)
    assert stats["corpus"]["documents"] == 1
    assert stats["corpus"]["risks_per_doc"]["median"] == 2
    assert stats["new"]["risks_total"] == 1
    assert stats["new"]["duplicate_titles_within_doc"] == 0
