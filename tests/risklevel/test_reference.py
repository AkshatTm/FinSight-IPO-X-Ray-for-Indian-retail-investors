"""C2.8: reference scores on the rolling window and thresholds fitted on train + dev only."""

from datetime import date
from pathlib import Path

import pytest

from finsight.risklevel import compute, load_config
from finsight.risklevel.reference import (
    apply_fit,
    deciles,
    fit_thresholds,
    read_scores,
    window_scores,
    write_scores,
)
from finsight.splits import SplitEntry, SplitsFile


def entry(ipo: str, slice_: str, day: str) -> SplitEntry:
    return SplitEntry(
        ipo_id=ipo, company=ipo, company_key=ipo, source="new", slice=slice_,  # type: ignore[arg-type]
        doc_date=date.fromisoformat(day),
    )  # fmt: skip


def synthetic(n_train: int = 40) -> tuple[SplitsFile, dict[str, float]]:
    ipos, scores = [], {}
    for i in range(n_train):
        ipo = f"tr-{i:02d}"
        ipos.append(entry(ipo, "train", f"2024-{1 + i % 12:02d}-15"))
        scores[ipo] = round(0.02 * i, 4)  # 0.00 ... 0.78
    for i in range(6):
        ipos.append(entry(f"dv-{i}", "dev", "2025-05-01"))
        scores[f"dv-{i}"] = 0.3 + 0.05 * i
    ipos.append(entry("te-0", "test", "2025-08-01"))
    scores["te-0"] = 5.0  # an extreme test score must not move any threshold
    return SplitsFile(ipos=ipos), scores


def test_thresholds_are_terciles_of_train_and_dev_only() -> None:
    splits, scores = synthetic()
    fit = fit_thresholds(scores, splits)
    assert fit["corpus_n"] == 46
    assert "te-0" not in fit["fit_ipos"]
    low, high = fit["thresholds"]["low_below"], fit["thresholds"]["high_from"]
    assert 0.2 < low < high < 0.6  # a 5.0 test score would have dragged "high_from" up
    assert len(fit["reference_quantiles"]) == 11
    assert fit["reference_quantiles"] == sorted(fit["reference_quantiles"])


def test_fit_refuses_too_few_or_concentrated_scores() -> None:
    splits, scores = synthetic(n_train=10)
    with pytest.raises(ValueError, match="need at least"):
        fit_thresholds(scores, splits)
    splits, _ = synthetic()
    flat = {e.ipo_id: 0.1 for e in splits.ipos}
    with pytest.raises(ValueError, match="too concentrated"):
        fit_thresholds(flat, splits)


def test_window_scores_follow_the_as_of_date_and_leave_test_ipos_out() -> None:
    splits, scores = synthetic()
    early = window_scores(scores, splits, date(2024, 3, 1))
    assert len(early) == 8  # train IPOs dated before March 2024 (Jan and Feb)
    late = window_scores(scores, splits, date(2026, 1, 1))
    assert 5.0 not in late  # eval window: no test IPO
    assert len(late) == 46
    product = window_scores(scores, splits, date(2026, 1, 1), kind="product")
    assert 5.0 in product
    own = window_scores(scores, splits, date(2026, 1, 1), exclude_ipo="tr-05")
    assert len(own) == 45


def test_scores_round_trip(tmp_path: Path) -> None:
    write_scores({"b": 0.25, "a": 0.5}, tmp_path / "s.csv")
    assert (tmp_path / "s.csv").read_text(encoding="utf-8").splitlines()[1] == "a,0.5000"
    assert read_scores(tmp_path / "s.csv") == {"a": 0.5, "b": 0.25}
    assert read_scores(tmp_path / "missing.csv") == {}


def test_deciles_have_eleven_points() -> None:
    d = deciles([float(i) for i in range(101)])
    assert d[0] == 0.0
    assert d[5] == 50.0
    assert d[-1] == 100.0
    with pytest.raises(ValueError, match="no reference"):
        deciles([])


def test_apply_fit_rewrites_the_config_and_keeps_comments() -> None:
    text = (Path(__file__).resolve().parents[2] / "configs" / "risklevel.yaml").read_text(
        encoding="utf-8"
    )
    splits, scores = synthetic()
    fit = fit_thresholds(scores, splits)
    new = apply_fit(text, fit, git_sha="abc1234", window_years=4)
    assert "provisional: false" in new
    assert "computed_on: abc1234" in new
    assert "window_years: 4" in new
    assert f"corpus_n: {fit['corpus_n']}" in new
    assert "# Risk level" in new  # comments survive
    assert new.count("thresholds:") == text.count("thresholds:")
    again = apply_fit(new, fit, git_sha="abc1234", window_years=4)
    assert again == new  # idempotent
    with pytest.raises(ValueError, match="exactly one"):
        apply_fit("provisional: true\n", fit, "x", 4)


def test_compute_uses_window_scores_when_given() -> None:
    cfg = dict(load_config())
    cfg["reference_quantiles"] = [0.0, 0.5, 1.0]
    stored = compute([], [], cfg)
    assert stored.corpus_n == int(cfg["corpus_n"])
    window = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    res = compute([], [], cfg, reference_scores=window)
    assert res.corpus_n == 11  # taken from the window, not from the config
    assert res.score == 0.0
    assert res.percentile == 0.0
    assert compute([], [], cfg, reference_scores=[]).corpus_n == int(cfg["corpus_n"])
