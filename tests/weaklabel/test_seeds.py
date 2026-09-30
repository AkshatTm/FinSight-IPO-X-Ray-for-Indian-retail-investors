from weaklabel_docs import COVER, FILLER, acme, make_doc, sections_for

from finsight.core.schemas import Count, ListValue, Money, TextValue
from finsight.weaklabel import LADDER_FIELDS, excel_values, find_seeds


def money(report, field_id):  # type: ignore[no-untyped-def]
    value = report.seeds[field_id].value
    assert isinstance(value, Money)
    return value.value_inr


def test_ladder_fields_exclude_offer_price_price_band_and_objects() -> None:
    assert set(LADDER_FIELDS) == {
        "fresh_issue_size", "ofs_shares", "ofs_amount", "total_issue_size", "face_value",
        "book_running_lead_managers", "registrar", "promoters",
    }  # fmt: skip


def test_clean_cover_gives_a_seed_for_every_ladder_field() -> None:
    doc, sections = acme()
    report = find_seeds(doc, sections)
    assert set(report.seeds) == set(LADDER_FIELDS), report.dropped
    assert money(report, "fresh_issue_size") == 3_000_000_000
    assert money(report, "ofs_amount") == 2_000_000_000
    assert money(report, "total_issue_size") == 5_000_000_000
    assert money(report, "face_value") == 10
    shares = report.seeds["ofs_shares"].value
    assert isinstance(shares, Count)
    assert shares.value == 4_000_000
    assert isinstance(report.seeds["registrar"].value, TextValue)
    promoters = report.seeds["promoters"].value
    assert isinstance(promoters, ListValue)
    assert promoters.items == ["RAVI KUMAR", "ANITA DESAI"]
    assert report.seeds["fresh_issue_size"].page == 1
    assert report.seeds["fresh_issue_size"].excel == "absent"


def test_placeholder_is_never_a_seed() -> None:
    cover = COVER.replace("₹ 2,000.00 MILLION", "₹ [●] MILLION")
    doc = make_doc([cover] + [FILLER] * 20)
    report = find_seeds(doc, sections_for(21))
    assert "ofs_amount" not in report.seeds
    assert report.dropped["ofs_amount"] == "placeholder"


def test_two_different_cover_values_are_ambiguous() -> None:
    other = COVER.replace("₹ 3,000.00 MILLION", "₹ 3,500.00 MILLION")
    doc = make_doc([COVER, other] + [FILLER] * 19)
    report = find_seeds(doc, sections_for(21))
    assert report.dropped["fresh_issue_size"] == "ambiguous"


def test_amounts_that_do_not_add_up_are_dropped_together() -> None:
    cover = COVER.replace("₹ 5,000.00 MILLION", "₹ 6,000.00 MILLION")
    doc = make_doc([cover] + [FILLER] * 20)
    report = find_seeds(doc, sections_for(21))
    for field_id in ("fresh_issue_size", "ofs_amount", "total_issue_size"):
        assert report.dropped[field_id] == "inconsistent"
    assert "face_value" in report.seeds


def test_excel_parsing_reads_only_the_numbers_it_can_trust() -> None:
    row = {
        "Total Issue Size": "10,000,000 shares (aggregating up to 500.00 Cr)",
        "Fresh Issue": "6,000,000 shares (aggregating up to 300.00 Cr)",
        "Offer for Sale": "4,000,000 shares of ₹10 (aggregating up to 200.00 Cr)",
        "Face Value per share": "10",
        "Final_Issue_Price": "500",
        "Price Band": None,
    }
    values = excel_values(row)
    assert isinstance(values["total_issue_size"], Money)
    assert values["total_issue_size"].value_inr == 5_000_000_000
    assert values["fresh_issue_size"].value_inr == 3_000_000_000  # type: ignore[union-attr]
    assert values["ofs_amount"].value_inr == 2_000_000_000  # type: ignore[union-attr]
    assert values["ofs_shares"] == Count(
        value=4_000_000, raw="4,000,000 shares", unit="shares"
    ) or (isinstance(values["ofs_shares"], Count) and values["ofs_shares"].value == 4_000_000)
    assert values["face_value"].value_inr == 10  # type: ignore[union-attr]
    assert "offer_price" not in values  # not a ladder field
    assert excel_values({"Fresh Issue": None, "Face Value per share": ""}) == {}


def test_excel_agreement_is_recorded_and_disagreement_drops_the_seed() -> None:
    doc, sections = acme()
    agree = find_seeds(doc, sections, excel_values({"Face Value per share": "10"}))
    assert agree.seeds["face_value"].excel == "agree"
    clash = find_seeds(doc, sections, excel_values({"Face Value per share": "2"}))
    assert clash.dropped["face_value"] == "excel_disagrees"


def test_an_unknown_registrar_guess_is_not_a_seed() -> None:
    cover = COVER.replace("KFin Technologies Limited", "Acme Share Services Private Limited")
    doc = make_doc([cover] + [FILLER] * 20)
    report = find_seeds(doc, sections_for(21))
    assert "registrar" not in report.seeds  # the generic fallback is only half-trusted


def test_mixed_case_name_lists_are_not_trusted_as_seeds() -> None:
    cover = COVER.replace(
        "RAVI KUMAR AND ANITA DESAI.", "Ravi Kumar and Anita Desai table C M Y K."
    )
    report = find_seeds(make_doc([cover] + [FILLER] * 20), sections_for(21))
    assert report.dropped["promoters"] == "not_cover_format"
