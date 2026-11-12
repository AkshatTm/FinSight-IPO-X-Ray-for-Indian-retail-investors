"""Platform Bench sheet helpers (Phase 4, CC-03 grows this module).

The sheet ``data/platform_bench/FinSight_Platform_Bench.xlsx`` is Akshat's hand-collected record of
what Groww, Zerodha and AngelOne show per IPO. It holds platform text, so it is never committed;
only ids and derived scores leave this module. Ids are normalised to the repo format (lowercase
hyphen slug, ``jio_platforms_2026`` -> ``jio-platforms-2026``).
"""

from __future__ import annotations

import re
from pathlib import Path

IPOS_SHEET = "IPOs"


def normalize_ipo_id(raw: str) -> str:
    """The repo's ``ipo_id`` format: lowercase, words joined by single hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", raw.strip().lower()).strip("-")


def read_ipo_ids(xlsx: Path) -> dict[str, str]:
    """``{normalised id: original id}`` from the IPOs tab (empty when the file is absent).

    Row 2 is the sheet's grey example row (Jio); it is read on purpose, so Jio is excluded too.
    """
    if not xlsx.exists():
        return {}
    import openpyxl

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    try:
        rows = wb[IPOS_SHEET].iter_rows(min_row=2, values_only=True)
        out: dict[str, str] = {}
        for row in rows:
            cell = row[0] if row else None
            if cell is None or not str(cell).strip():
                continue
            out[normalize_ipo_id(str(cell))] = str(cell).strip()
        return out
    finally:
        wb.close()
