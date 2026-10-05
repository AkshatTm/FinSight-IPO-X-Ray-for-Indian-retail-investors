"""C2.6: choosing the novelty threshold from rated pairs (E22)."""

import importlib.util
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from finsight.risks import load_bank
from finsight.risks.bank_build import write_parquet
from finsight.risks.novelty_tau import (
    MIN_PAIRS,
    Pair,
    choose_tau,
    nearest_other,
    precision_at,
    read_ratings,
    result,
    sample_pairs,
    write_sheet,
)
from finsight.splits import SplitEntry, SplitsFile

ROOT = Path(__file__).resolve().parents[2]


def pair(i: int, sim: float) -> Pair:
    return Pair(f"x-2025#{i}", "y-2024", f"title {i}", sim, a_company="X", b_company="Y")


def rated_ladder() -> list[tuple[float, str]]:
    """Pairs judged 'same' only from similarity 0.80 up (a clean ladder)."""
    out = [(0.62 + 0.01 * i, "no") for i in range(18)]  # 0.62 .. 0.79
    out += [(0.80 + 0.01 * i, "yes") for i in range(20)]  # 0.80 .. 0.99
    return out


def test_nearest_other_skips_the_issuers_own_rows() -> None:
    ref = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]])
    got = nearest_other(np.array([[1.0, 0.0]]), ref, ["own", "b", "c"], "own")
    assert got[0][0] == 2  # row 0 is the issuer; row 2 beats row 1
    assert got[0][1] == pytest.approx(0.7071, abs=1e-3)
    assert nearest_other(np.array([[1.0, 0.0]]), ref, ["own"] * 3, "own") == []


def test_sample_pairs_is_even_over_bins_and_deterministic() -> None:
    pairs = [pair(i, 0.60 + 0.4 * (i % 400) / 400) for i in range(2000)]
    a, b = sample_pairs(pairs, 80, bins=8), sample_pairs(pairs, 80, bins=8)
    assert [p.pair_id for p in a] == [p.pair_id for p in b]
    assert len(a) == 80
    top = [p for p in a if p.similarity >= 0.90]
    assert len(top) >= 20  # the high end is not starved
    assert sample_pairs([pair(1, 0.3)], 10) == []  # below 0.60 is never a candidate


def test_choose_tau_takes_the_lowest_similarity_meeting_the_rule() -> None:
    # cumulative: 0.79 -> 20/21, 0.78 -> 20/22 (0.909, ok), 0.77 -> 20/23 (fails)
    tau = choose_tau(rated_ladder())
    assert tau == pytest.approx(0.78)
    yes, n = precision_at(rated_ladder(), tau)
    assert (yes, n) == (20, 22)


def test_a_noisy_low_end_pushes_tau_up() -> None:
    rated = [*rated_ladder(), (0.84, "no"), (0.85, "no")]  # two misses inside the top block
    tau = choose_tau(rated)
    assert tau is not None
    assert tau > 0.78
    yes, n = precision_at(rated, tau)
    assert yes / n >= 0.90
    assert n >= MIN_PAIRS


def test_no_tau_when_nothing_meets_the_rule() -> None:
    assert choose_tau([(0.9, "no")] * 30) is None
    assert choose_tau([(0.9, "yes")] * (MIN_PAIRS - 1)) is None  # too few to support a threshold
    res = result([(0.9, "no")] * 30, 0.8)
    assert res["tau"] is None
    assert "keep the placeholder" in res["note"]


def test_unsure_is_left_out_of_precision() -> None:
    rated = rated_ladder() + [(0.95, "unsure")] * 10
    assert precision_at(rated, 0.8) == (20, 20)  # the ten unsure at 0.95 are not counted
    assert result(rated, 0.8)["n_unsure"] == 10


def test_result_reports_curve_and_interval() -> None:
    res = result(rated_ladder(), 0.80)
    assert res["tau"] == pytest.approx(0.78)
    assert res["n_at_tau"] == 22
    assert 0.7 < res["ci95"][0] < res["precision_at_tau"]
    assert [c["tau"] for c in res["curve"]][:2] == [0.6, 0.65]
    assert res["curve"][0]["n"] == 38
    assert "human:akshat" in res["label_source"]


def test_sheet_is_blind_and_ratings_round_trip(tmp_path: Path) -> None:
    pairs = [pair(1, 0.91), pair(2, 0.70)]
    write_sheet(pairs, tmp_path / "sheet.csv", tmp_path / "key.json")
    text = (tmp_path / "sheet.csv").read_text(encoding="utf-8")
    assert "0.91" not in text
    assert "similarity" not in text
    assert read_ratings(tmp_path / "sheet.csv", tmp_path / "key.json") == []  # nothing rated yet
    rows = text.splitlines()
    rows[1] += "yes"  # last column is same_risk
    rows[2] += "NO"
    (tmp_path / "sheet.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    got = read_ratings(tmp_path / "sheet.csv", tmp_path / "key.json")
    assert sorted(got) == [(0.7, "no"), (0.91, "yes")]
    assert set(json.loads((tmp_path / "key.json").read_text(encoding="utf-8")).values()) == {
        0.91,
        0.7,
    }


def entry(ipo: str, slice_: str, company: str, day: str) -> SplitEntry:
    return SplitEntry(
        ipo_id=ipo, company=company, company_key=company.lower(), source="new", slice=slice_,
        doc_date=date.fromisoformat(day),
    )  # fmt: skip


def test_collect_pairs_uses_dev_queries_and_a_window_without_test_ipos(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "novelty_pairs", ROOT / "scripts/novelty_pairs.py"
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    splits = SplitsFile(
        ipos=[
            entry("tr-2024", "train", "Train Co", "2024-02-01"),
            entry("dv-2025", "dev", "Dev Co", "2025-03-01"),
            entry("te-2024", "test", "Test Co", "2024-09-01"),
        ]
    )
    vec = {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [0.9, 0.1]}

    def row(ipo: str, split: str, company: str, rid: str, key: str, year: int) -> dict:
        return {"risk_id": f"{ipo}#{rid}", "company": company, "year": year,
                "title": f"{key} {rid}", "embedding": vec[key], "ipo_id": ipo, "doc_date": "",
                "split": split}  # fmt: skip

    rows = [
        row("tr-2024", "train", "Train Co", "r1", "b", 2024),
        row("te-2024", "test", "Test Co", "r1", "a", 2024),  # nearest of all, but a test IPO
        row("dv-2025", "dev", "Dev Co", "r1", "c", 2025),
    ]
    write_parquet(rows, tmp_path / "bank.parquet")
    bank = load_bank(tmp_path / "bank.parquet", years=None)
    extra = mod.parquet_columns(tmp_path / "bank.parquet")

    def source(e: SplitEntry) -> list:
        return [SimpleNamespace(rid="r1", title=f"{e.ipo_id} title", body=f"body of {e.ipo_id}")]

    pairs = mod.collect_pairs(bank, extra, splits, source)
    assert len(pairs) == 1
    p = pairs[0]
    assert p.query_id == "dv-2025#r1"
    assert p.ref_ipo_id == "tr-2024"  # the test IPO is not a neighbour even though it is closer
    assert p.a_company == "Dev Co"
    assert p.a_text == "body of dv-2025"
