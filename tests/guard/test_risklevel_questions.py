"""B2.6a: questions about the risk level are facts; decisions and ratings are still refused."""

import pytest

from finsight.guard.advice import check_advice


@pytest.mark.parametrize(
    "question",
    [
        "How risky is this IPO?",
        "Is this IPO risky?",
        "Is it risky?",
        "What is the risk level?",
        "Explain the risk level",
        "Why is the risk level high?",
        "How risky is it compared to other IPOs?",
        "What are the biggest risks?",
        "kitna risky hai ye ipo",
        "risky hai kya",
        "क्या यह आईपीओ जोखिम भरा है?",
    ],
)
def test_risk_level_questions_pass(question: str) -> None:
    assert not check_advice(question).blocked


@pytest.mark.parametrize(
    "question",
    [
        "Should I apply?",
        "Is this IPO safe?",
        "Is it safe to invest?",
        "Is this a good IPO?",
        "Is the risk worth it for me?",
        "Is it high risk, so should I avoid it?",
        "safe hai kya",
    ],
)
def test_decisions_and_ratings_are_still_refused(question: str) -> None:
    assert check_advice(question).blocked
