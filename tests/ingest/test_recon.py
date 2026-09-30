import json
import zipfile
from pathlib import Path

import openpyxl
import pytest

from finsight.ingest import recon
from finsight.ingest.recon import (
    ALLOWED_COLUMNS,
    classify_cover,
    flatten_text,
    is_forbidden_column,
    normalize_company,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("DRAFT RED HERRING PROSPECTUS\nDated March 1, 2016", "drhp"),
        ("RED HERRING PROSPECTUS\nDated March 11, 2016", "rhp"),
        ("(Please scan this QR code to view this Red Herring Prospectus)", "rhp"),
        ("PROSPECTUS\nDated November 7, 2025", "prospectus"),
        ("Some annual report", "unknown"),
        ("", "unknown"),
        # The first title phrase on the cover decides, not any later mention (real dataset cases):
        ("RED HERRING PROSPECTUS Dated 2016 ... (This Draft Red Herring Prospectus)", "rhp"),
        ("C M Y K Prospectus Dated 2010 ... read with the Red Herring Prospectus", "prospectus"),
        ("(cid:51)(cid:53) Dated: February 05, 2016", "unknown"),
    ],
)
def test_classify_cover(text: str, expected: str) -> None:
    assert classify_cover(text) == expected


def test_draft_wins_over_rhp_wording() -> None:
    # A DRHP cover contains the words "Red Herring Prospectus" too.
    assert classify_cover("Draft Red Herring Prospectus") == "drhp"


def test_flatten_text_walks_nested_page_lists() -> None:
    page = [["RED HERRING ", "PROSPECTUS"], "image", [["Dated"]], 3, None]
    assert flatten_text(page) == "RED HERRING  PROSPECTUS image Dated"


@pytest.mark.parametrize(
    ("column", "forbidden"),
    [
        ("Success_Open", True),
        ("Success_Close", True),
        ("NSE_Open", True),
        ("BSE_Last_Trade", True),
        ("Brokers_Avoid", True),
        ("Members_Subscribe", True),
        ("Total_subscriptions", True),
        ("day_1_retail", True),
        ("Fresh Issue", False),
        ("Face Value per share", False),
    ],
)
def test_forbidden_columns(column: str, forbidden: bool) -> None:
    assert is_forbidden_column(column) is forbidden


def test_allowed_columns_never_include_forbidden_ones() -> None:
    assert not [c for c in ALLOWED_COLUMNS if is_forbidden_column(c)]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Edserv Softsystems Limited IPO", "edserv softsystems"),
        ("Mahindra Holidays and Resorts India Ltd IPO", "mahindra holidays and resorts india"),
        ("HDB Financial Services Ltd.", "hdb financial services"),
        ("  Meesho   Limited ", "meesho"),
    ],
)
def test_normalize_company(raw: str, expected: str) -> None:
    assert normalize_company(raw) == expected


@pytest.fixture
def tiny_dataset(tmp_path: Path) -> tuple[Path, Path]:
    xlsx = tmp_path / "data.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "data_ordered"
    ws.append(["Issuer Company", "Close Year", "Fresh Issue", "Success_Open", "File_Rename_1st"])
    ws.append(["Acme Limited IPO", "2016", "100 Cr", "1", " 1_RHP.pdf"])
    ws.append(["Beta Ltd IPO", "2019", None, "0", " 2.pdf"])
    wb.save(xlsx)
    zpath = tmp_path / "texts.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("d/1_RHP.json", json.dumps({"Page_0": [["RED HERRING PROSPECTUS"]]}))
        z.writestr("d/2.json", json.dumps({"Page_0": [["PROSPECTUS"]]}))
        z.writestr("d/3_DRHP.json", json.dumps({"Page_0": [["Draft Red Herring Prospectus"]]}))
    return xlsx, zpath


def test_summarize_excel_reports_coverage_and_hides_forbidden(
    tiny_dataset: tuple[Path, Path],
) -> None:
    summary = recon.summarize_excel(tiny_dataset[0])
    assert summary.n_rows == 2
    assert summary.years == {"2016": 1, "2019": 1}
    assert summary.coverage["Fresh Issue"] == pytest.approx(0.5)
    assert "Success_Open" not in summary.coverage


def test_summarize_zip_classifies_by_cover_and_name(tiny_dataset: tuple[Path, Path]) -> None:
    summary = recon.summarize_zip(tiny_dataset[1])
    assert summary.n_entries == 3
    assert summary.by_cover == {"rhp": 1, "prospectus": 1, "drhp": 1}
    assert summary.by_name_pattern == {"N_RHP.json": 1, "N.json": 1, "N_DRHP.json": 1}
    assert summary.by_name_and_cover["N.json -> prospectus"] == 1


def test_sample_rows_are_truncated_and_exclude_forbidden(tiny_dataset: tuple[Path, Path]) -> None:
    rows = recon.sample_rows(tiny_dataset[0], n=5, max_chars=5)
    assert len(rows) == 2
    for row in rows:
        assert "Success_Open" not in row
        assert all(len(str(v)) <= 5 for v in row.values())


def test_demo_overlap_matches_normalised_names(tiny_dataset: tuple[Path, Path]) -> None:
    found = recon.demo_overlap(tiny_dataset[0], ["Acme Limited", "Meesho Limited"])
    assert found == ["Acme Limited"]
