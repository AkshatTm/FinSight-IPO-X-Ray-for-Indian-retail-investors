import json
from pathlib import Path
from typing import Any

import pytest

from finsight.evaluate.gold import (
    DEFAULT_DOC,
    FIELDS,
    expected_keys,
    self_consistency,
    template_rows,
    validate_file,
    validate_row,
)

IPO = "urban-company-2025"  # a demo IPO: RHP has 577 pages


def row(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ipo_id": IPO,
        "field_id": "fresh_issue_size",
        "doc": "rhp",
        "value_raw": "₹ 4,720 million",
        "page": 12,
        "quote": "a Fresh Issue of [●] Equity Shares aggregating up to ₹ 4,720 million",
        "status": "present",
        "labelled_at": "2026-10-08",
        "notes": "",
    }
    return base | over


def problems(**over: Any) -> list[str]:
    return validate_row(row(**over))


def test_the_eleven_fields_and_their_documents() -> None:
    assert len(FIELDS) == 11
    assert DEFAULT_DOC["offer_price"] == "prospectus"
    assert DEFAULT_DOC["total_issue_size"] == "prospectus"
    assert DEFAULT_DOC["fresh_issue_size"] == "rhp"
    assert len(expected_keys()) == 11 * 10  # 11 fields x 10 demo IPOs


def test_a_good_row_has_no_problems() -> None:
    assert problems() == []


def test_unknown_ipo_field_and_doc() -> None:
    assert any("unknown ipo" in p for p in problems(ipo_id="nope-2025"))
    assert any("unknown field" in p for p in problems(field_id="revenue"))
    assert any("doc" in p for p in problems(doc="drhp"))


def test_present_needs_value_page_quote_and_date() -> None:
    assert any("value_raw" in p for p in problems(value_raw=""))
    assert any("page" in p for p in problems(page=None))
    assert any("quote" in p for p in problems(quote=""))
    assert any("labelled_at" in p for p in problems(labelled_at="8 Oct"))


def test_page_must_exist_in_the_document() -> None:
    assert any("page" in p for p in problems(page=0))
    assert any("577" in p for p in problems(page=578))
    assert problems(page=577) == []


def test_value_must_appear_in_the_quote_ignoring_whitespace() -> None:
    assert problems(quote="aggregating up to ₹ 4,720\n million by the company") == []
    assert any("quote" in p for p in problems(quote="aggregating up to ₹ 800 crore"))


def test_money_count_and_range_values_must_parse() -> None:
    assert any("money" in p for p in problems(value_raw="four thousand", quote="four thousand"))
    ok = problems(field_id="ofs_shares", value_raw="10,181,585", quote="up to 10,181,585 shares")
    assert ok == []
    bad = problems(field_id="price_band", value_raw="₹ 440", quote="₹ 440")
    assert any("range" in p for p in bad)
    good = problems(field_id="price_band", value_raw="₹ 103 to ₹ 108", quote="₹ 103 to ₹ 108 per")
    assert good == []


def test_placeholder_status_needs_a_blank_value() -> None:
    ok = problems(
        field_id="ofs_amount", value_raw="[●]", quote="aggregating up to ₹ [●] million",
        status="placeholder",
    )  # fmt: skip
    assert ok == []
    assert any("placeholder" in p for p in problems(status="placeholder"))


def test_not_in_document_has_no_value_or_page() -> None:
    ok = problems(status="not_in_document", value_raw="", page=None, quote="")
    assert ok == []
    assert any("not_in_document" in p for p in problems(status="not_in_document"))


def test_list_fields_take_lists_of_text() -> None:
    lst = problems(
        field_id="book_running_lead_managers", value_raw=["Axis Capital", "JM Financial"],
        quote="Axis Capital Limited JM Financial Limited",
    )  # fmt: skip
    assert lst == []
    assert any("list" in p for p in problems(field_id="promoters", value_raw="Mr X"))
    assert any("quote" in p for p in problems(
        field_id="promoters", value_raw=["Mr X"], quote="Mr Y"
    ))  # fmt: skip


def test_objects_are_purpose_amount_pairs() -> None:
    quote = "Funding capex ₹ 1,900.00 million General corporate purposes [●]"
    ok = problems(
        field_id="objects_of_offer", quote=quote,
        value_raw=[["Funding capex", "₹ 1,900.00 million"], ["General corporate purposes", "[●]"]],
    )  # fmt: skip
    assert ok == []
    assert any("pair" in p for p in problems(field_id="objects_of_offer", value_raw=["x"]))


def _write(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", "utf-8")
    return path


def test_validate_file_reports_line_numbers_and_duplicates(tmp_path: Path) -> None:
    f = _write(tmp_path / "gold.jsonl", [row(), row(), row(page=0, field_id="face_value")])
    issues = validate_file(f)
    assert any(i.startswith("line 2") and "duplicate" in i for i in issues)
    assert any(i.startswith("line 3") for i in issues)


def test_validate_file_can_require_completeness(tmp_path: Path) -> None:
    f = _write(tmp_path / "gold.jsonl", [row()])
    assert validate_file(f) == []
    issues = validate_file(f, require_complete=True)
    assert len(issues) == 11 * 10 - 1
    assert all(i.startswith("missing") for i in issues)


def test_template_has_every_key_and_no_values() -> None:
    rows = template_rows()
    assert len(rows) == 11 * 10
    assert {(r["ipo_id"], r["field_id"], r["doc"]) for r in rows} == expected_keys()
    assert all(r["value_raw"] == "" and r["page"] is None and r["status"] == "" for r in rows)
    assert len(template_rows("meesho-2025")) == 11


def test_an_unfilled_template_fails_validation(tmp_path: Path) -> None:
    f = _write(tmp_path / "t.jsonl", template_rows("meesho-2025"))
    assert len(validate_file(f)) == 11


def test_self_consistency_compares_values_not_strings(tmp_path: Path) -> None:
    a = [row(), row(field_id="face_value", value_raw="₹ 1", quote="₹ 1 each", page=3)]
    b = [
        row(value_raw="₹ 472 crore"),  # same as 4,720 million
        row(field_id="face_value", value_raw="₹ 2", quote="₹ 2 each", page=3),
    ]
    report = self_consistency(_write(tmp_path / "a.jsonl", a), _write(tmp_path / "b.jsonl", b))
    assert report.n == 2
    assert report.agree == 1
    assert report.disagreements == [(IPO, "face_value", "rhp")]
    assert report.rate == pytest.approx(0.5)
