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


# --- AI-prefilled gold v1 (ADR-035): looser quote matching, evidence on not_in_document ---


def test_quote_match_ignores_case_and_footnote_marks() -> None:
    assert problems(value_raw="₹ 321", quote="AT A PRICE OF ₹ 321^ PER EQUITY SHARE") == []
    assert problems(value_raw="₹ 4,720 MILLION", quote="up to ₹ 4,720 million #") == []
    assert any("quote" in p for p in problems(value_raw="₹ 322", quote="₹ 321^ per share"))


def test_bullet_placeholder_is_a_placeholder() -> None:
    ok = problems(
        field_id="ofs_amount", value_raw="₹ [•] million", status="placeholder",
        quote="aggregating up to ₹ [●] million",
    )  # fmt: skip
    assert ok == []


def test_text_values_may_wrap_across_table_lines() -> None:
    quote = "Registrar to the Offer KFin Technologies Tel: +91 40 6716 2222 Limited"
    assert problems(field_id="registrar", value_raw="KFin Technologies Limited", quote=quote) == []
    wrong = problems(field_id="registrar", value_raw="Limited KFin Technologies", quote=quote)
    assert any("quote" in p for p in wrong)  # words must stay in order


def test_list_items_may_be_interleaved_with_contact_details() -> None:
    quote = (
        "Axis Capital Limited Sagar Jatakiya E-mail: a@b.in HSBC Securities and Capital Markets "
        "Harsh Thakkar / Tel: +91 22 6864 1289 (India) Private Limited"
    )
    ok = problems(
        field_id="book_running_lead_managers", quote=quote,
        value_raw=[
            "Axis Capital Limited",
            "HSBC Securities and Capital Markets (India) Private Limited",
        ],
    )  # fmt: skip
    assert ok == []
    bad = problems(field_id="book_running_lead_managers", value_raw=["Nomura"], quote=quote)
    assert any("quote" in p for p in bad)


def test_objects_rows_may_be_interleaved_with_numbers() -> None:
    quote = (
        "1. Capital expenditure to be 9,272 7,055 2,217 - incurred by our Company 2. Repayment 400"
    )
    ok = problems(
        field_id="objects_of_offer", quote=quote,
        value_raw=[
            ["Capital expenditure to be incurred by our Company", "9,272"],
            ["Repayment", "400"],
        ],
    )  # fmt: skip
    assert ok == []


def test_not_in_document_may_keep_the_evidence_page_and_quote() -> None:
    quote = "Our Company will not receive any proceeds from the Offer"
    ok = problems(status="not_in_document", value_raw="", page=21, quote=quote)
    assert ok == []
    assert any("page" in p for p in problems(status="not_in_document", value_raw="", page=9999))
    assert any("value" in p for p in problems(status="not_in_document", value_raw="₹ 5"))


def test_label_source_is_optional_and_checked() -> None:
    assert problems(label_source="ai_assisted_verified") == []
    assert problems(label_source="hand") == []
    assert any("label_source" in p for p in problems(label_source="guess"))


def test_convert_prefill_fixes_the_format_only() -> None:
    from finsight.evaluate.gold import convert_prefill

    src = row(
        doc="pro", notes="[AI-prefilled, needs human verification] Footnote ^ after the number."
    )
    obj = row(
        field_id="objects_of_offer",
        value_raw=["Capex :: 9,272", "Other :: [●]"],
        quote="Capex 9,272 Other [●]",
        notes="[AI-prefilled, needs human verification]",
    )
    a, b = convert_prefill([src, obj])
    assert a["doc"] == "prospectus"
    assert a["label_source"] == "ai_assisted_verified"
    assert a["notes"] == "Footnote ^ after the number."
    assert a["value_raw"] == src["value_raw"]
    assert a["quote"] == src["quote"]
    assert b["value_raw"] == [["Capex", "9,272"], ["Other", "[●]"]]
    assert b["notes"] == ""


def test_note_references_glued_to_a_word_are_ignored() -> None:
    quote = "Funding general 5. [●] corporate purposes(1)(2) Total"
    ok = problems(
        field_id="objects_of_offer", quote=quote,
        value_raw=[["Funding general corporate purposes", "[●]"]],
    )  # fmt: skip
    assert ok == []
