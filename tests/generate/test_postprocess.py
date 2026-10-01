import pytest

from finsight.core.schemas import Passage
from finsight.generate.postprocess import LoopDetector, clean_answer, is_dump, trim_loops
from finsight.generate.prompts import NOT_FOUND, build_prompt

PASSAGE_TEXT = (
    "The Registrar to the Offer is KFin Technologies Limited, having its office at Selenium "
    "Building, Tower B, Plot 31 and 32, Financial District, Nanakramguda, Hyderabad 500032, "
    "Telangana, India, and the contact person is the Compliance Officer of the registrar."
)


def passage(text: str = PASSAGE_TEXT) -> Passage:
    return Passage(
        id="i:p3:c0",
        ipo_id="i",
        doc_type="rhp",
        section_id="s",
        page_start=3,
        page_end=3,
        text=text,
        char_to_bbox=[],
    )


def test_good_answer_passes_untouched():
    answer = "The registrar is KFin Technologies Limited [1]."
    cleaned = clean_answer(answer, [passage()])
    assert cleaned.reason is None
    assert cleaned.text == answer
    assert not cleaned.trimmed


def test_citation_only_becomes_not_found():
    for text in ("[1][1][1][1]", "[1] [2].", "  [1]\n"):
        cleaned = clean_answer(text, [passage()])
        assert cleaned.text == NOT_FOUND["en"]
        assert cleaned.reason in ("citation_only", "empty")


def test_empty_becomes_not_found_in_the_asked_language():
    cleaned = clean_answer("   ", [passage()], "hi")
    assert cleaned.text == NOT_FOUND["hi"]
    assert cleaned.reason == "empty"


def test_repeated_sentence_is_cut_and_keeps_the_first_copies():
    answer = "The registrar is KFin [1]. " * 8
    text, trimmed = trim_loops(answer)
    assert trimmed
    assert text.count("The registrar is KFin") == 2


def test_citation_run_collapses():
    text, trimmed = trim_loops("The registrar is KFin [1][1][1][1][1].")
    assert trimmed
    assert text == "The registrar is KFin [1]."


def test_pasted_passage_is_rejected_but_a_short_quote_is_not():
    assert is_dump(PASSAGE_TEXT + " [1]", [passage()])
    cleaned = clean_answer(PASSAGE_TEXT + " [1]", [passage()])
    assert cleaned.reason == "dump"
    assert cleaned.text == NOT_FOUND["en"]
    assert not is_dump("The registrar is KFin Technologies Limited [1].", [passage()])


def test_paraphrase_with_a_long_name_is_not_a_dump():
    answer = (
        "KFin Technologies Limited is the registrar, and investors can write to its compliance "
        "officer in Hyderabad for any query about the offer [1]."
    )
    assert clean_answer(answer, [passage()]).reason is None


def test_loop_detector_stops_on_a_repeating_tail_not_on_normal_text():
    detector = LoopDetector()
    assert not any(
        detector.feed(w) for w in ["The", "registrar", "is", "KFin", "Technologies", "[1]."]
    )
    looping = LoopDetector()
    stopped = [looping.feed("[1][2] ") for _ in range(12)]
    assert any(stopped)
    assert not stopped[0]


def test_loop_detector_ignores_plain_repeated_digits():
    detector = LoopDetector()
    assert not detector.feed("₹ 1,000,000 million")


def test_prompt_rules_ask_for_units_names_and_own_words():
    en = build_prompt("q", [passage()], "en").text
    hi = build_prompt("q", [passage()], "hi").text
    assert "AND its unit" in en
    assert "Never paste" in en
    assert "रोमन" in hi
    assert "अपने शब्दों में" in hi


FRESH = "The fresh issue is up to ₹ 26,260 million [1]."


def test_devanagari_digits_become_ascii_digits():
    from finsight.generate.postprocess import ascii_digits

    assert ascii_digits("₹ ४,७२० million") == ("₹ 4,720 million", True)
    assert ascii_digits("₹ 4,720 million") == ("₹ 4,720 million", False)


def test_clean_answer_converts_digits_and_flags_it():
    passages = [passage("The offer price is ₹ 321 per equity share.")]
    cleaned = clean_answer("ऑफ़र प्राइस ₹ ३२१ है [1]।", passages, "hi")
    assert cleaned.reason is None
    assert cleaned.digits_converted
    assert "321" in cleaned.text


@pytest.mark.parametrize(
    "answer",
    [
        "The fresh issue is ₹ 2,626 crore [1].",  # the passage says million
        "The fresh issue is ₹ 262.60 crore [1].",  # wrong, and another unit
    ],
)
def test_converted_unit_is_rejected(answer):
    from finsight.generate.postprocess import converted_units

    passages = [passage("The fresh issue is up to ₹ 26,260 million.")]
    if "2,626" in answer:
        assert converted_units(answer, passages) == ["₹ 2,626 crore"]
        assert clean_answer(answer, passages).reason == "unit_converted"
    else:
        assert converted_units(answer, passages) == []  # a wrong number is the verifier's job


def test_unit_copied_as_written_passes():
    passages = [passage("The fresh issue is up to ₹ 26,260 million.")]
    assert clean_answer(FRESH, passages).reason is None


@pytest.mark.parametrize(
    "answer",
    [
        "Investors should be careful before applying [1].",
        "This is a good investment opportunity [1].",
        "We recommend reading the risk factors [1].",
        "निवेशकों को सावधान रहना चाहिए [1]।",
        "इस IPO में निवेश की सलाह दी जाती है [1]।",
    ],
)
def test_investor_opinions_and_cautions_are_rejected(answer):
    assert clean_answer(answer, [passage()]).reason == "opinion"


def test_plain_facts_are_not_opinions():
    from finsight.generate.postprocess import has_opinion

    assert not has_opinion("The registrar is KFin Technologies Limited [1].")
    assert not has_opinion("इस ऑफ़र का रजिस्ट्रार KFin Technologies Limited है [1]।")
