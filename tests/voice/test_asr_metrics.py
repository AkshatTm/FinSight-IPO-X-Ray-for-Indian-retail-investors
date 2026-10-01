import pytest
from hypothesis import given
from hypothesis import strategies as st

from finsight.voice import cer, cer_with_spaces, normalize, wer
from finsight.voice.metrics import edit_distance


def test_normalisation_makes_spelling_variants_equal() -> None:
    assert normalize("ऑफ़र प्राइस कितना है?") == normalize("ऑफर प्राइस कितना है")
    assert normalize("कुल इश्यू ₹ ४,७२०") == normalize("कुल इश्यू 4 720")
    assert normalize("  पता।  ") == "पता"
    assert normalize("मैं") == normalize("मैँ")  # chandrabindu and anusvara


def test_known_error_rates() -> None:
    assert cer("प्रमोटर कौन हैं", "प्रमोटर कौन हैं") == 0.0
    assert cer("abcd", "abxd") == pytest.approx(0.25)
    assert cer("आई पी ओ", "आईपीओ") == 0.0  # spaces are not errors in the primary figure
    assert cer_with_spaces("आई पी ओ", "आईपीओ") > 0.0
    assert wer("one two three four", "one two tree four") == pytest.approx(0.25)


def test_empty_reference() -> None:
    assert cer("", "") == 0.0
    assert cer("", "कुछ") == 1.0


def test_edit_distance_basics() -> None:
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance(["a", "b"], ["a"]) == 1


@given(st.text(min_size=1, max_size=40))
def test_identical_text_has_zero_error(text: str) -> None:
    assert cer(text, text) == 0.0
    assert wer(text, text) == 0.0


@given(st.text(max_size=30), st.text(max_size=30))
def test_edit_distance_is_symmetric_and_bounded(a: str, b: str) -> None:
    assert edit_distance(a, b) == edit_distance(b, a)
    assert edit_distance(a, b) <= max(len(a), len(b))


@given(st.text(min_size=1, max_size=30), st.text(max_size=30))
def test_cer_is_never_negative(ref: str, hyp: str) -> None:
    assert cer(ref, hyp) >= 0.0
