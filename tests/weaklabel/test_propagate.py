from weaklabel_docs import FILLER, acme, make_doc, sections_for

from finsight.core.schemas import ListValue, TextValue
from finsight.extract import get_field
from finsight.normalize import parse_amount
from finsight.weaklabel import find_answer, find_seeds, propagate


def positives(field_id: str):  # type: ignore[no-untyped-def]
    doc, sections = acme()
    seed = find_seeds(doc, sections).seeds[field_id]
    return propagate(doc, sections, get_field(field_id), seed)


def test_seed_value_found_in_other_wordings_becomes_a_positive() -> None:
    found = positives("fresh_issue_size")
    by_page = {e.page: e for e in found}
    assert set(by_page) == {1, 19}  # the cover and The Offer
    offer = by_page[19]
    assert offer.answer_text == "Rs. 300 crore"  # same money as ₹ 3,000.00 million
    assert offer.context[offer.answer_start :].startswith(offer.answer_text)
    assert not offer.is_impossible
    assert offer.field_id == "fresh_issue_size"
    assert offer.ipo_id == "acme-2019"
    assert offer.passage_id == "acme-2019:prospectus:p19:c0"


def test_every_positive_span_is_exactly_the_answer_text() -> None:
    for field_id in ("fresh_issue_size", "ofs_shares", "ofs_amount", "face_value", "registrar"):
        for e in positives(field_id):
            assert e.context[e.answer_start : e.answer_start + len(e.answer_text)] == e.answer_text


def test_same_number_without_the_metric_keyword_is_not_a_positive() -> None:
    value = parse_amount("₹ 3,000.00 million")
    text = "Our revenue from operations was ₹ 3,000.00 million in Fiscal 2019."
    assert find_answer(get_field("fresh_issue_size"), value, text) is None  # type: ignore[arg-type]
    good = "The Fresh Issue is of ₹ 3,000.00 million."
    assert find_answer(get_field("fresh_issue_size"), value, good) is not None  # type: ignore[arg-type]


def test_names_match_fuzzily_ltd_and_limited_case_and_punctuation() -> None:
    registrar = get_field("registrar")
    seed = TextValue(text="KFin Technologies Limited")
    text = "The registrar to the offer is KFIN TECHNOLOGIES LTD. and it keeps the register."
    span = find_answer(registrar, seed, text)
    assert span is not None
    assert text[span[0] : span[1]] == "KFIN TECHNOLOGIES LTD."
    assert find_answer(registrar, seed, "Registrar: Bigshare Services Limited") is None


def test_a_list_trains_on_one_span_covering_all_its_names() -> None:
    promoters = get_field("promoters")
    seed = ListValue(items=["RAVI KUMAR", "ANITA DESAI"])
    text = "Our Promoters are Anita Desai and Ravi Kumar, who hold 70% of the shares."
    span = find_answer(promoters, seed, text)
    assert span is not None
    assert text[span[0] : span[1]] == "Anita Desai and Ravi Kumar"
    assert find_answer(promoters, seed, "Our Promoter is Ravi Kumar.") is None  # partial list


def test_positives_are_capped_per_field_and_document() -> None:
    offer = "The Fresh Issue aggregates ₹ 3,000.00 million. " * 3
    pages = [offer] * 18 + [FILLER] * 3
    doc = make_doc(pages)
    seed_doc, sections = acme()
    seed = find_seeds(seed_doc, sections).seeds["fresh_issue_size"]
    found = propagate(doc, sections_for(21), get_field("fresh_issue_size"), seed, max_positives=5)
    assert len(found) == 5
    assert len({e.passage_id for e in found}) == 5  # one per passage
