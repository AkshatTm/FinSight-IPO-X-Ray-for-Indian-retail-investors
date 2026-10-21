"""Exclusion rule of the handoff pack (C-ADR-02 strict, Phase 4)."""

from __future__ import annotations

from finsight.handoff import excluded_ipos, splits_by_ipo

SPLITS = {
    "version": 1,
    "train_cut": "2025-06-19",
    "ipos": [
        {"ipo_id": "a-2024", "company_key": "a", "slice": "train", "source": "new"},
        {"ipo_id": "b-2025", "company_key": "b", "slice": "dev", "source": "new"},
        {"ipo_id": "c-2026", "company_key": "c", "slice": "test", "source": "new"},
        {"ipo_id": "d-2025", "company_key": "d", "slice": "dev", "source": "showcase"},
    ],
    "excluded": [{"ipo_id": "sme-2026", "reason": "SME"}],
    "demo": ["demo-2026"],
    "bench": ["c-2026"],
    "bench_dev": [],
}


def test_every_exclusion_source_is_listed_with_its_reason() -> None:
    ex = excluded_ipos(SPLITS, ["d-2025"], ["c-2026"], ["jio-platforms-2026"])
    ipos = ex["ipos"]
    assert set(ipos) == {"c-2026", "sme-2026", "demo-2026", "d-2025", "jio-platforms-2026"}
    assert ipos["c-2026"]["reasons"] == ["bench", "bench_v1", "test_slice"]
    assert ipos["jio-platforms-2026"]["reasons"] == ["platform_bench"]
    assert "a-2024" not in ipos
    assert "b-2025" not in ipos


def test_splits_by_ipo_marks_excluded_rows_and_counts_trainable() -> None:
    ex = excluded_ipos(SPLITS, ["d-2025"], [], [])
    out = splits_by_ipo(SPLITS, ex)
    rows = {r["ipo_id"]: r for r in out["ipos"]}
    assert rows["a-2024"]["excluded"] is False
    assert rows["c-2026"]["excluded"] is True
    assert rows["sme-2026"]["slice"] == "excluded"
    assert out["counts"] == {"train": 1, "dev": 1, "excluded": 4}
