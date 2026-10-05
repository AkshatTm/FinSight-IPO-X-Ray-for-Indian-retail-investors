"""A small synthetic split shared by the split tests (no real data)."""

from collections.abc import Callable
from datetime import date

import pytest

from finsight.splits import SplitEntry, SplitsFile
from finsight.splits.store import ExcludedEntry


def entry(ipo_id: str, company: str, slice_: str, *, d: date | None = None,
          year: int | None = None, source: str = "new") -> SplitEntry:  # fmt: skip
    from finsight.risks import company_key

    return SplitEntry(ipo_id=ipo_id, company=company, company_key=company_key(company),
                      source=source, slice=slice_, doc_date=d, close_year=year)  # type: ignore[arg-type]  # fmt: skip


@pytest.fixture
def make_entry() -> Callable[..., SplitEntry]:
    return entry


@pytest.fixture
def splits() -> SplitsFile:
    return SplitsFile(
        train_cut=date(2025, 6, 1),
        ipos=[
            entry("old-a-2021", "Old A Limited", "train", year=2021, source="corpus"),
            entry("old-b-2022", "Old B Limited", "train", year=2022, source="corpus"),
            entry("old-c-2018", "Old C Limited", "train", year=2018, source="corpus"),
            entry("new-a-2024", "New A Limited", "train", d=date(2024, 5, 1)),
            entry("new-b-2025", "New B Limited", "train", d=date(2025, 3, 1)),
            entry("dev-a-2025", "Dev A Limited", "dev", d=date(2025, 7, 1)),
            entry(
                "show-dev-2025", "Show Dev Limited", "dev", d=date(2025, 2, 1), source="showcase"
            ),
            entry("test-a-2025", "Test A Limited", "test", d=date(2025, 6, 1), source="showcase"),
            entry("test-b-2026", "Test B Limited", "test", d=date(2026, 3, 1)),
            entry("test-c-2026", "Test C Limited", "test", d=date(2026, 5, 1)),
        ],
        excluded=[ExcludedEntry(ipo_id="broken-2025", reason="failed: parse timeout")],
        demo=["test-c-2026"],
    )
