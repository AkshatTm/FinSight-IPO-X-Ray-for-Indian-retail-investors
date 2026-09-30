from finsight.core.schemas import (
    Candidate,
    Count,
    DocType,
    ListValue,
    Money,
    Placeholder,
    TextValue,
    Value,
)
from finsight.extract import get_field, select_field
from finsight.normalize import parse_amount


def money(text: str) -> Money:
    value = parse_amount(text)
    assert isinstance(value, Money)
    return value


def cand(
    field_id: str,
    value: Value,
    extractor: str = "rules",
    page: int = 3,
    score: float = 0.9,
    doc: DocType = "rhp",
) -> Candidate:
    raw = getattr(value, "raw", "x")
    return Candidate(
        field_id=field_id, extractor=extractor, doc_type=doc, raw=raw, value=value, page=page,
        score=score,
    )  # fmt: skip


FRESH = "fresh_issue_size"


def test_one_extractor_found_it_is_verified_with_the_extractor_named() -> None:
    sel = select_field(get_field(FRESH), {"rhp": [cand(FRESH, money("₹ 4,720 million"))]})
    assert sel.chosen is not None
    assert sel.verdict == "verified"
    assert sel.reason_code == "verified"
    assert "rules" in sel.reason
    assert "p. 3" in sel.reason


def test_two_extractors_agreeing_is_verified_and_the_primary_is_chosen() -> None:
    rules = cand(FRESH, money("₹ 4,720 million"), "rules", 3)
    qa = cand(FRESH, money("₹ 472 crore"), "qa_pretrained", 12, 0.99)  # same money, other unit
    sel = select_field(get_field(FRESH), {"rhp": [qa, rules]})
    assert sel.chosen == rules  # the field's primary extractor wins, not the higher score
    assert sel.verdict == "verified"
    assert "agree" in sel.reason


def test_disagreement_keeps_the_primary_but_is_flagged() -> None:
    rules = cand(FRESH, money("₹ 4,720 million"))
    qa = cand(FRESH, money("₹ 400 million"), "qa_pretrained", 3)  # same page, other number
    sel = select_field(get_field(FRESH), {"rhp": [rules, qa]})
    assert sel.chosen == rules
    assert sel.verdict == "unverifiable"
    assert sel.reason_code == "extractors_disagree"
    assert "400" in sel.reason


def test_a_different_value_from_another_page_is_not_a_contradiction() -> None:
    rules = cand("face_value", money("₹ 1"), page=1)
    qa = cand("face_value", money("₹ 200,000"), "qa_pretrained", 14, 1.0)  # another sentence
    sel = select_field(get_field("face_value"), {"rhp": [rules, qa]})
    assert sel.verdict == "verified"
    assert sel.chosen == rules
    assert "Found by rules" in sel.reason


def test_any_qa_candidate_that_matches_confirms_even_if_not_its_best() -> None:
    rules = cand("face_value", money("₹ 1"), page=1)
    wrong = cand("face_value", money("₹ 200,000"), "qa_pretrained", 14, 1.0)
    right = cand("face_value", money("₹ 1"), "qa_pretrained", 1, 0.8)
    sel = select_field(get_field("face_value"), {"rhp": [rules, wrong, right]})
    assert "agree" in sel.reason


def test_pure_offer_for_sale_ignores_model_guesses() -> None:
    junk = cand(FRESH, money("₹ 100 million"), "qa_pretrained", 8)
    sel = select_field(get_field(FRESH), {"rhp": [junk]}, pure_ofs=True)
    assert sel.chosen is None
    assert sel.reason_code == "not_in_document"


def test_companion_note_prefers_the_rules_value() -> None:
    blank = cand("ofs_amount", Placeholder(raw="[●]"))
    rules = cand("ofs_amount", money("₹ 14,280 million"), doc="prospectus", page=12, score=0.7)
    junk = cand(
        "ofs_amount", money("₹ 1 million"), extractor="qa_pretrained", doc="prospectus",
        page=9, score=0.99,
    )  # fmt: skip
    sel = select_field(get_field("ofs_amount"), {"rhp": [blank], "prospectus": [rules, junk]})
    assert "14,280" in sel.reason


def test_fallback_extractor_is_used_when_the_primary_finds_nothing() -> None:
    qa = cand(FRESH, money("₹ 4,720 million"), "qa_pretrained", 12)
    sel = select_field(get_field(FRESH), {"rhp": [qa]})
    assert sel.chosen == qa
    assert sel.verdict == "verified"


def test_placeholder_in_the_primary_document_is_reported_as_such() -> None:
    blank = cand("ofs_amount", Placeholder(raw="₹ [●] million"))
    wrong_qa = cand("ofs_amount", money("₹ 1 million"), "qa_pretrained", 40)
    sel = select_field(get_field("ofs_amount"), {"rhp": [blank, wrong_qa]})
    assert sel.chosen == blank
    assert sel.verdict == "unverifiable"
    assert sel.reason_code == "placeholder"
    assert "[●]" in sel.reason


def test_placeholder_reason_points_to_the_companion_value() -> None:
    blank = cand("ofs_amount", Placeholder(raw="[●]"))
    real = cand("ofs_amount", money("₹ 14,280 million"), doc="prospectus", page=3)
    sel = select_field(get_field("ofs_amount"), {"rhp": [blank], "prospectus": [real]})
    assert sel.reason_code == "placeholder"
    assert "Prospectus" in sel.reason
    assert "p. 3" in sel.reason


def test_primary_document_follows_the_field_spec() -> None:
    total = get_field("total_issue_size")  # read from the Prospectus (ADR-023)
    rhp = cand("total_issue_size", money("₹ 100 million"), doc="rhp")
    pro = cand("total_issue_size", money("₹ 19,000 million"), doc="prospectus")
    sel = select_field(total, {"rhp": [rhp], "prospectus": [pro]})
    assert sel.chosen == pro


def test_nothing_found() -> None:
    sel = select_field(get_field("registrar"), {"rhp": []})
    assert sel.chosen is None
    assert sel.verdict == "unverifiable"
    assert sel.reason_code == "not_in_document"


def test_missing_section_is_reported_as_such() -> None:
    sel = select_field(get_field("face_value"), {"rhp": []}, missing_sections=["capital_structure"])
    assert sel.reason_code == "section_not_found"
    assert "capital_structure" in sel.reason


def test_pure_offer_for_sale_has_no_fresh_issue_and_no_objects() -> None:
    for field_id in (FRESH, "objects_of_offer"):
        sel = select_field(get_field(field_id), {"rhp": []}, pure_ofs=True)
        assert sel.chosen is None
        assert sel.verdict == "verified"
        assert sel.reason_code == "not_in_document"
        assert "offer for sale" in sel.reason.lower()
    other = select_field(get_field("registrar"), {"rhp": []}, pure_ofs=True)
    assert other.verdict == "unverifiable"


def test_text_and_list_values_compare_ignoring_case_and_order() -> None:
    a = cand("registrar", TextValue(text="KFin Technologies Limited"))
    b = cand("registrar", TextValue(text="KFIN TECHNOLOGIES LIMITED"), "qa_pretrained")
    assert select_field(get_field("registrar"), {"rhp": [a, b]}).verdict == "verified"
    la = cand("promoters", ListValue(items=["A B", "C D"]))
    lb = cand("promoters", ListValue(items=["C D", "A B"]), "qa_pretrained")
    assert select_field(get_field("promoters"), {"rhp": [la, lb]}).verdict == "verified"
    part = cand("promoters", ListValue(items=["A B"]), "qa_pretrained")  # names only some
    assert select_field(get_field("promoters"), {"rhp": [la, part]}).verdict == "verified"
    other = cand("promoters", ListValue(items=["X Y"]), "qa_pretrained")
    assert select_field(get_field("promoters"), {"rhp": [la, other]}).reason_code == (
        "extractors_disagree"
    )
    wide = cand("registrar", TextValue(text="KFin Technologies"), "qa_pretrained")
    full = cand("registrar", TextValue(text="KFin Technologies Limited"))
    assert select_field(get_field("registrar"), {"rhp": [full, wide]}).verdict == "verified"


def test_counts_compare_by_value() -> None:
    a = cand("ofs_shares", Count(value=11_051_746, raw="11,051,746"))
    b = cand("ofs_shares", Count(value=11_051_746, raw="11051746"), "qa_pretrained")
    assert select_field(get_field("ofs_shares"), {"rhp": [a, b]}).verdict == "verified"
