"""C1.4: splits.yaml freeze guard, manifests and the leakage check (negative tests included)."""

from collections.abc import Callable
from pathlib import Path

import pytest

from finsight.splits import (
    FrozenSplitError,
    Manifest,
    SplitEntry,
    SplitsFile,
    check_manifests,
    load_splits,
    read_manifests,
    save_splits,
    showcase_mismatches,
    write_manifest,
)


def m(name: str, kind: str, ids: list[str], inputs: list[str] | None = None) -> Manifest:
    return Manifest(artefact=name, kind=kind, ipo_ids=ids, inputs=inputs or [],  # type: ignore[arg-type]
                    written_by="test")  # fmt: skip


# ---- splits.yaml -----------------------------------------------------------------------------


def test_round_trip(tmp_path: Path, splits: SplitsFile) -> None:
    path = tmp_path / "splits.yaml"
    save_splits(splits, path)
    again = load_splits(path)
    assert again == splits
    assert path.read_text(encoding="utf-8").startswith("# Phase 3 time split")


def test_frozen_file_needs_an_adr(tmp_path: Path, splits: SplitsFile) -> None:
    path = tmp_path / "splits.yaml"
    splits.frozen = True
    save_splits(splits, path)
    with pytest.raises(FrozenSplitError, match="C-ADR"):
        save_splits(splits, path)
    save_splits(splits, path, adr="C-ADR-13")
    assert load_splits(path).changed_by_adr == ["C-ADR-13"]


def test_subsets_must_sit_in_their_slice(splits: SplitsFile) -> None:
    data = splits.model_dump()
    data["bench"] = ["dev-a-2025"]
    with pytest.raises(ValueError, match="bench must be test"):
        SplitsFile.model_validate(data)
    data["bench"], data["bench_dev"] = [], ["test-b-2026"]
    with pytest.raises(ValueError, match="bench_dev must be dev"):
        SplitsFile.model_validate(data)


def test_showcase_roles_compared_with_demo_ipos(splits: SplitsFile) -> None:
    assert showcase_mismatches(splits, {"test-a-2025": "test", "show-dev-2025": "dev"}) == []
    bad = showcase_mismatches(splits, {"test-a-2025": "dev", "gone-2025": "test"})
    assert len(bad) == 2
    assert "says dev" in bad[1]
    assert "missing" in bad[0]


# ---- manifests -------------------------------------------------------------------------------


def test_manifest_round_trip_sorts_and_dedupes(tmp_path: Path) -> None:
    path = write_manifest(m("risk_bank", "train", ["b-2024", "a-2024", "a-2024"]), tmp_path)
    assert path.name == "risk_bank.json"
    got = read_manifests(tmp_path)
    assert got[0].ipo_ids == ["a-2024", "b-2024"]
    assert '"n_ipos": 2' in path.read_text(encoding="utf-8")


def test_manifest_name_must_match_the_file(tmp_path: Path) -> None:
    write_manifest(m("risk_bank", "train", []), tmp_path)
    (tmp_path / "risk_bank.json").rename(tmp_path / "other.json")
    with pytest.raises(ValueError, match="does not match"):
        read_manifests(tmp_path)


def test_no_manifest_folder_means_no_manifests(tmp_path: Path) -> None:
    assert read_manifests(tmp_path / "missing") == []


# ---- leakage ---------------------------------------------------------------------------------


def test_clean_manifests_pass(splits: SplitsFile) -> None:
    ok = [
        m("weak", "train", ["old-a-2021", "new-a-2024"]),
        m("tau", "fit", ["dev-a-2025", "show-dev-2025"]),
        m("ref_eval", "eval_reference", ["new-b-2025"]),
        m("risk_eval", "eval", ["test-a-2025", "test-b-2026"]),
        m("ref_product", "product_reference", ["test-c-2026", "old-a-2021"]),
    ]
    assert check_manifests(ok, splits) == []


@pytest.mark.parametrize("kind", ["train", "fit", "eval_reference"])
def test_planted_test_id_is_caught(splits: SplitsFile, kind: str) -> None:
    leaks = check_manifests([m("bad", kind, ["old-a-2021", "test-b-2026"])], splits)
    assert [(v.item, v.reason) for v in leaks] == [("test-b-2026", "test/bench IPO")]


def test_planted_company_key_is_caught(
    splits: SplitsFile, make_entry: Callable[..., SplitEntry]
) -> None:
    twin = make_entry("test-b-old-2019", "Test B Ltd.", "train", year=2019, source="corpus")
    splits.ipos.append(twin)
    leaks = check_manifests([m("bank", "train", ["test-b-old-2019"])], splits)
    assert len(leaks) == 1
    assert "same company as test IPO test-b-2026" in leaks[0].reason


def test_excluded_and_unknown_ids_are_caught(splits: SplitsFile) -> None:
    leaks = check_manifests([m("bank", "train", ["broken-2025", "nobody-2024"])], splits)
    assert {v.reason for v in leaks} == {"excluded IPO used", "unknown ipo_id (not in splits.yaml)"}


def test_product_reference_cannot_feed_training_or_fitting(splits: SplitsFile) -> None:
    ref = m("ref_product", "product_reference", ["test-c-2026"])
    fit = m("thresholds", "fit", ["dev-a-2025"], inputs=["ref_product"])
    leaks = check_manifests([ref, fit], splits)
    assert [str(v) for v in leaks] == [
        "thresholds: ref_product: product reference used as an input"
    ]
