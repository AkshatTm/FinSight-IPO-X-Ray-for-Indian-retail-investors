"""Leakage guard on the committed split and manifests (C-ADR-02; CLAUDE.md hard rule).

Runs in `poe test`. It reads only `configs/splits.yaml`, `configs/demo_ipos.yaml` and
`data/manifests/` (never processed data). Until the split is frozen on real data (C1.4's
real-data run after C1.3), the checks on the committed files are skipped with that reason;
the logic itself is tested on fixtures in `tests/splits/`.
"""

from pathlib import Path

import pytest

from finsight.ingest import list_demo_ipos
from finsight.splits import check_manifests, load_splits, read_manifests, showcase_mismatches

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "configs" / "splits.yaml"
MANIFESTS = ROOT / "data" / "manifests"

needs_split = pytest.mark.skipif(
    not SPLITS.is_file(),
    reason="split not frozen yet: run `python -m finsight.splits build "
    "--freeze` after C1.3 (C05 C1.4)",
)


@needs_split
def test_split_is_frozen() -> None:
    assert load_splits(SPLITS).frozen


@needs_split
def test_showcase_roles_match_demo_ipos() -> None:
    roles = {s.ipo_id: s.split for s in list_demo_ipos()}
    assert showcase_mismatches(load_splits(SPLITS), roles) == []


@needs_split
def test_no_test_or_bench_ipo_in_any_training_or_fitting_artefact() -> None:
    leaks = check_manifests(read_manifests(MANIFESTS), load_splits(SPLITS))
    assert not leaks, "\n".join(str(v) for v in leaks)


def test_manifests_need_a_frozen_split() -> None:
    """A manifest committed before the split exists could never be checked."""
    if read_manifests(MANIFESTS):
        assert SPLITS.is_file(), "data/manifests/ has files but configs/splits.yaml is missing"
