from pathlib import Path

import pytest

from finsight.core.config import Settings
from finsight.evaluate.guard_eval import compare
from finsight.guard import check_question
from finsight.guard.clf import load_scorer


def test_a_scorer_decides_advice_but_privacy_stays_rule_based() -> None:
    low, high = (lambda q: 0.1), (lambda q: 0.9)
    assert check_question("Should I apply for this IPO?", scorer=low).blocked is False
    result = check_question("What is the registrar?", scorer=high)
    assert result.blocked
    assert result.reason == "advice_intent"
    assert result.category == "classifier"
    # a rule that also matches names the kind of request, so the refusal can be worded for it
    assert check_question("Will it double on listing day?", scorer=high).category == "forecast"
    # privacy is refused by the rules even when the classifier thinks the question is fine
    private = check_question("What is the home address of the company's CEO?", scorer=low)
    assert private.blocked
    assert private.reason == "privacy"


def test_default_backend_is_the_keyword_rules() -> None:
    assert Settings().guard.backend == "keyword"
    assert check_question("Should I apply for this IPO?").blocked
    assert not check_question("Who is the registrar?").blocked


def test_missing_weights_say_how_to_fetch_them(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="kaggle_clf fetch full"):
        load_scorer(tmp_path)


def row(q: str, lang: str, label: str, p: float) -> dict[str, object]:
    return {"question": q, "language": lang, "label": label, "p_advice": p}


def test_comparison_scores_both_on_the_same_questions() -> None:
    test = [
        row("Should I apply for this IPO?", "en", "advice", 0.95),
        row("Is this IPO a good buy?", "en", "advice", 0.2),
        row("Who is the registrar?", "en", "fact", 0.1),
        row("क्या ये IPO खरीदना सही रहेगा?", "hi", "advice", 0.9),
    ]
    out = compare({"best_seed_by_val_f1": 13, "best_seed_predictions": {"test": test}})
    assert out["n_test"] == 4
    assert out["muril"]["overall"]["block_rate"]["hits"] == 2  # missed the "good buy" question
    assert out["muril"]["overall"]["false_block_rate"]["hits"] == 0
    assert out["keyword"]["overall"]["block_rate"]["n"] == 3
    assert all(d["keyword"] != d["muril"] for d in out["disagreements"])
