"""C1.4: the `configs/ipo_universe.csv` contract that C1.1 must produce (C02 §2)."""

from pathlib import Path

import pytest

from finsight.splits import UNIVERSE_COLUMNS, UniverseError, load_universe

HEADER = ",".join(UNIVERSE_COLUMNS)


def write(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "ipo_universe.csv"
    path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")
    return path


ROW = "acme-tools-2024,Acme Tools Limited,both,rhp,2024-03-01,2024-03-12,https://www.sebi.gov.in/x.pdf,{sha},612,parsed,"
SHA = "a" * 64


def test_columns_are_the_c02_contract() -> None:
    assert UNIVERSE_COLUMNS == (
        "ipo_id", "company", "exchange", "doc_type", "doc_date", "listing_date",
        "source_url", "sha256", "pages", "status", "reason",
    )  # fmt: skip


def test_reads_a_valid_row(tmp_path: Path) -> None:
    rows = load_universe(write(tmp_path, ROW.format(sha=SHA)))
    assert len(rows) == 1
    r = rows[0]
    assert r.ipo_id == "acme-tools-2024"
    assert r.pages == 612
    assert r.status == "parsed"
    assert r.doc_date.isoformat() == "2024-03-01"


def test_empty_optional_cells_are_none(tmp_path: Path) -> None:
    row = "acme-tools-2024,Acme Tools Limited,NSE,rhp,2024-03-01,,https://x,,,listed,"
    r = load_universe(write(tmp_path, row))[0]
    assert r.listing_date is None
    assert r.sha256 is None
    assert r.pages is None


def test_wrong_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "u.csv"
    path.write_text("ipo_id,company\nx-2024,X\n", encoding="utf-8")
    with pytest.raises(UniverseError, match="columns"):
        load_universe(path)


@pytest.mark.parametrize(
    ("row", "match"),
    [
        (ROW.format(sha=SHA).replace("acme-tools-2024", "Acme Tools"), "ipo_id"),
        (ROW.format(sha=SHA).replace(",parsed,", ",downloaded-ish,"), "status"),
        (ROW.format(sha="xyz"), "sha256"),
        (ROW.format(sha=SHA).replace(",rhp,", ",drhp,"), "doc_type"),
        (ROW.format(sha=SHA).replace(",parsed,", ",failed,"), "reason"),
    ],
)
def test_bad_rows_name_the_column(tmp_path: Path, row: str, match: str) -> None:
    with pytest.raises(UniverseError, match=match):
        load_universe(write(tmp_path, row))


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    row = ROW.format(sha=SHA)
    with pytest.raises(UniverseError, match="duplicate"):
        load_universe(write(tmp_path, row, row))
