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
