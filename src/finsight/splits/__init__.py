"""Phase 3 time split and leakage guard (C02 §4–5, C-ADR-02, C-ADR-03).

Assigns every IPO (corpus, newly collected, showcase) to train, dev or test so that every train
document is dated before every test document; writes ``configs/splits.yaml``; reads and writes
the artefact manifests in ``data/manifests/``; checks them for leaks (by ``ipo_id`` and company
key); and answers "which IPOs are past IPOs for a document dated X" with the rolling 4-year
reference window (eval and product kinds). Also defines the ``configs/ipo_universe.csv``
contract that C1.1 must produce. Other packages are wired to it in C2.1, C2.7, C2.8 and C3.4.
"""

from finsight.splits.assign import (
    IpoRecord,
    SplitError,
    SplitResult,
    SplitRules,
    assign,
    check_strict,
)
from finsight.splits.schema import (
    FINAL_STATUSES,
    UNIVERSE_COLUMNS,
    UniverseError,
    UniverseRow,
    load_universe,
)
from finsight.splits.store import (
    ExcludedEntry,
    FrozenSplitError,
    SplitEntry,
    SplitsFile,
    load_splits,
    save_splits,
    showcase_mismatches,
    to_splits_file,
)

__all__ = [
    "FINAL_STATUSES",
    "UNIVERSE_COLUMNS",
    "ExcludedEntry",
    "FrozenSplitError",
    "IpoRecord",
    "SplitEntry",
    "SplitError",
    "SplitResult",
    "SplitRules",
    "SplitsFile",
    "UniverseError",
    "UniverseRow",
    "assign",
    "check_strict",
    "load_splits",
    "load_universe",
    "save_splits",
    "showcase_mismatches",
    "to_splits_file",
]
