"""Platform Bench id format and sheet reading (the sheet itself is never committed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from finsight.bench import normalize_ipo_id, read_ipo_ids


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("jio_platforms_2026", "jio-platforms-2026"),
        (" Lenskart  2025 ", "lenskart-2025"),
        ("ather-energy-2025", "ather-energy-2025"),
        ("A&B Ltd_2024", "a-b-ltd-2024"),
    ],
)
def test_normalize_ipo_id(raw: str, want: str) -> None:
    assert normalize_ipo_id(raw) == want


def test_read_ipo_ids_from_a_synthetic_sheet(tmp_path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "IPOs"
    ws.append(["ipo_id", "company"])
    ws.append(["jio_platforms_2026", "Jio"])
    ws.append([None, None])
    ws.append(["Some_Co_2025", "Some"])
    path = tmp_path / "sheet.xlsx"
    wb.save(path)
    assert read_ipo_ids(path) == {
        "jio-platforms-2026": "jio_platforms_2026",
        "some-co-2025": "Some_Co_2025",
    }
    assert read_ipo_ids(tmp_path / "missing.xlsx") == {}
