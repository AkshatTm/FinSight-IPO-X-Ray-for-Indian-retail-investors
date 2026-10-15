"""E19 readability helpers."""

from finsight.risks.readability import fkgl, flesch_reading_ease, syllables


def test_syllables() -> None:
    assert [syllables(w) for w in ("cat", "table", "make", "regulation", "a")] == [1, 2, 1, 4, 1]


def test_plain_text_scores_easier_than_legalese() -> None:
    plain = "We may lose money. Our customers may pay late. This may hurt cash."
    legal = (
        "Notwithstanding the aforementioned contractual obligations, the Company's "
        "profitability may be materially and adversely affected by unforeseen regulatory "
        "developments pertaining to environmental compliance requirements."
    )
    assert fkgl(plain) < 6 < fkgl(legal)
    assert flesch_reading_ease(plain) > flesch_reading_ease(legal)


def test_empty_text_is_zero() -> None:
    assert fkgl("") == 0.0
    assert flesch_reading_ease("   ") == 0.0
