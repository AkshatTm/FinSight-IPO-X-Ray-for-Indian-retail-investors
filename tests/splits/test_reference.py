"""C1.4: rolling 4-year reference window (C02 §5, C-ADR-03)."""

from collections.abc import Callable
from datetime import date

from finsight.splits import (
    SplitEntry,
    SplitsFile,
    in_window,
    ipos_before,
    reference_config,
    window_n,
)
from finsight.splits.reference import window_summary, years_before


def ids(splits: SplitsFile, as_of: date, **kw: object) -> list[str]:
    return [e.ipo_id for e in ipos_before(splits, as_of, 4, **kw)]  # type: ignore[arg-type]


def test_config_window_is_four_years() -> None:
    assert reference_config()["window_years"] == 4


def test_eval_window_has_no_test_ipos_and_no_later_ones(splits: SplitsFile) -> None:
    got = ids(splits, date(2026, 3, 1), kind="eval", exclude_ipo="test-b-2026")
    # old-a closed in 2021: outside 2022..2025 for a 2026 document
    assert got == ["old-b-2022", "new-a-2024", "show-dev-2025", "new-b-2025", "dev-a-2025"]
    assert "test-a-2025" not in got  # an earlier test IPO is still left out in eval


def test_product_window_includes_earlier_test_ipos_but_not_the_upload(splits: SplitsFile) -> None:
    got = ids(splits, date(2026, 5, 1), kind="product", exclude_ipo="test-c-2026")
    assert "test-a-2025" in got
    assert "test-b-2026" in got
    assert "test-c-2026" not in got


def test_never_looks_ahead(splits: SplitsFile) -> None:
    got = ids(splits, date(2025, 3, 1), kind="product")
    assert "new-b-2025" not in got  # same day is not "before"
    assert all(e.doc_date is None or e.doc_date < date(2025, 3, 1)
               for e in ipos_before(splits, date(2025, 3, 1), 4, kind="product"))  # fmt: skip


def test_corpus_rows_count_by_close_year(splits: SplitsFile) -> None:
    old_b = next(e for e in splits.ipos if e.ipo_id == "old-b-2022")
    old_c = next(e for e in splits.ipos if e.ipo_id == "old-c-2018")
    assert in_window(old_b, date(2026, 1, 15), 4)  # 2022..2025
    assert not in_window(old_b, date(2022, 12, 31), 4)  # never in its own close year
    assert not in_window(old_c, date(2023, 1, 1), 4)  # 2019..2022
    assert in_window(old_c, date(2022, 1, 1), 4)  # 2018..2021


def test_issuer_left_out_by_company_key(
    splits: SplitsFile, make_entry: Callable[..., SplitEntry]
) -> None:
    splits.ipos.append(make_entry("new-a-again-2025", "New A Ltd.", "train", d=date(2025, 1, 1)))
    got = ids(splits, date(2025, 5, 1), kind="eval", exclude_company="New A Limited")
    assert "new-a-2024" not in got
    assert "new-a-again-2025" not in got


def test_window_n_per_test_ipo(splits: SplitsFile) -> None:
    sizes = window_n(splits, 4)
    assert set(sizes) == {"test-a-2025", "test-b-2026", "test-c-2026"}
    assert sizes["test-b-2026"] == 5
    assert window_summary(sizes).startswith("eval window n per test IPO: min ")


def test_leap_day() -> None:
    assert years_before(date(2028, 2, 29), 4) == date(2024, 2, 29)
    assert years_before(date(2028, 2, 29), 1) == date(2027, 2, 28)
