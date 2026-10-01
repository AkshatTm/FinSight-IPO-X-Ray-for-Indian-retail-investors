"""Advice, forecast and rating detector: table-driven in English, Hindi and Hinglish.

The probes below were written after the rules and before any of them was scored: they are not
part of Akshat's advice set, so they measure how the rules do on wording they were not built on.
"""

import pytest

from finsight.guard import check_advice, normalize_question

ADVICE = [
    # English
    ("Is it wise to put my savings into this IPO?", "personal"),
    ("Will the stock list above the issue price?", "forecast"),
    ("Do you think Tata Capital will perform well?", "decision"),
    ("Which IPO has more upside, Meesho or Lenskart?", "comparison"),
    ("Is this a safe bet for my retirement money?", "decision"),
    ("Can you tell me if I should subscribe?", "decision"),
    ("What will be the listing day price of Ather?", "forecast"),
    ("How much profit will I make on listing?", "forecast"),
    ("Is this IPO overvalued?", "rating"),
    ("Tell me if Groww is a good buy.", "decision"),
    ("Should investors apply for the retail category or HNI?", "decision"),
    ("Give me a rating for this IPO out of 10.", "rating"),
    ("Is the GMP showing it will list at a premium?", "gmp"),
    ("Would applying with two demat accounts increase my allotment chances?", "strategy"),
    ("Which stock gives better returns, Hexaware or Ather?", "comparison"),
    ("Is Meesho a good long term investment?", "rating"),
    ("Will the company be profitable next year?", "forecast"),
    ("What returns can I expect in 3 years?", "forecast"),
    # Hinglish
    ("Kya main ye IPO le lu?", "decision"),
    ("IPO se kitna profit hoga?", "forecast"),
    ("Ye stock upar jayega kya?", "forecast"),
    ("Meesho aur Lenskart me se kaunsa lena sahi hai?", "comparison"),
    ("Is IPO me paisa dalna chahiye?", "decision"),
    ("Mujhe ye IPO lena chahiye ya nahi?", "decision"),
    ("Kya ye IPO mehnga hai?", "rating"),
    ("GMP achha hai toh apply karu?", "decision"),
    # Hindi
    ("क्या मुझे यह आईपीओ लेना चाहिए?", "decision"),
    ("कंपनी के शेयर लिस्टिंग के दिन कितने पर खुलेंगे?", "forecast"),
    ("क्या यह आईपीओ पैसा दोगुना कर देगा?", "forecast"),
    ("इस आईपीओ में कितनी कमाई होगी?", "forecast"),
    ("आप क्या सलाह देंगे, अप्लाई करूँ?", "decision"),
    ("कौन सा आईपीओ बेहतर है, ग्रो या मीशो?", "comparison"),
    ("इस कंपनी की रेटिंग बताओ।", "rating"),
    ("क्या मैं अपनी बीवी के खाते से भी भर सकता हूँ?", "strategy"),
    ("क्या शेयर का भाव ऊपर जाएगा?", "forecast"),
    ("अगले साल कंपनी का मुनाफ़ा कितना होगा?", "forecast"),
]

FACTUAL = [
    # English
    "What is the price band of the Groww IPO?",
    "How many equity shares are reserved for retail investors?",
    "What is the minimum bid lot?",
    "Who are the book running lead managers?",
    "Who is the registrar to the offer?",
    "What are the objects of the offer?",
    "What is the face value of each equity share?",
    "Does the company have any outstanding litigation?",
    "What is the total offer size?",
    "What is the issue opening date?",
    "What are the main risk factors?",
    "How do I apply for the IPO through UPI?",
    "Can retail investors bid at the cut-off price?",
    "What is the allotment date?",
    "How is the basis of allotment decided?",
    "What is the book building process?",
    "What is the employee reservation discount?",
    "What was the revenue from operations in fiscal 2025?",
    "What percentage of the offer is for qualified institutional buyers?",
    "Is the company profitable?",
    "What is the total borrowing of the company?",
    "What does the prospectus say about promoter holding after the offer?",
    "Is the offer for sale by promoters or other shareholders?",
    "Where will the equity shares be listed?",
    "Which exchanges will the shares list on?",
    "What does GMP mean?",
    "Who are the promoters of the company?",
    "Is there a lock-in on promoter shares?",
    # Hinglish
    "Retail ke liye kitne shares reserve hai?",
    "IPO kab khulega?",
    "Allotment kab hoga?",
    "Company ka revenue kitna hai?",
    "Is IPO me promoters kaun hai?",
    "Minimum lot size kitna hai?",
    "Price band kya hai?",
    "UPI se apply kaise karu?",
    "Kya IPO ke baad promoters ki holding kam hogi?",
    # Hindi
    "प्राइस बैंड क्या है?",
    "रजिस्ट्रार कौन है?",
    "कंपनी के प्रमोटर कौन हैं?",
    "इश्यू कब खुलेगा?",
    "न्यूनतम कितने शेयरों के लिए आवेदन कर सकते हैं?",
    "ऑफर में कितने शेयर रिटेल निवेशकों के लिए रिज़र्व हैं?",
    "कंपनी पर कोई मुकदमा चल रहा है क्या?",
    "आईपीओ से जुटाया पैसा किस काम में लगेगा?",
    "इस आईपीओ का अंकित मूल्य क्या है?",
    "मैं आवेदन कैसे करूँ?",
    "जीएमपी का मतलब क्या होता है?",
]


@pytest.mark.parametrize(("question", "category"), ADVICE)
def test_advice_questions_are_blocked(question: str, category: str) -> None:
    result = check_advice(question)
    assert result.blocked, question
    assert result.reason == "advice_intent"
    assert result.matched


@pytest.mark.parametrize("question", FACTUAL)
def test_factual_questions_pass(question: str) -> None:
    result = check_advice(question)
    assert not result.blocked, f"{question!r} blocked as {result.category}: {result.matched!r}"
    assert result.reason is None


def test_the_category_names_the_kind_of_request() -> None:
    assert check_advice("Should I apply for this IPO?").category == "decision"
    assert check_advice("Will it double in a year?").category == "forecast"
    assert check_advice("Is it overpriced?").category == "rating"
    assert check_advice("Which is better, Groww or Lenskart?").category == "comparison"
    assert check_advice("Is the GMP a good sign?").category in {"gmp", "rating"}


def test_spelling_variants_of_hindi_questions_are_one_question() -> None:
    assert normalize_question("निवेश करूँ?") == normalize_question("निवेश करूं?")
    assert normalize_question("ज़्यादा") == normalize_question("ज्यादा")
    assert normalize_question("  Should   I  APPLY? ") == "should i apply?"
    assert check_advice("निवेश करूँ?").blocked
    assert check_advice("क्या भाव ज़्यादा है?").blocked
    assert not check_advice("").blocked


def test_a_how_to_question_is_procedural_even_with_a_subjunctive_verb() -> None:
    assert not check_advice("मैं आवेदन कैसे करूँ?").blocked
    assert not check_advice("Kahan se apply karu?").blocked
    assert check_advice("आवेदन करूँ या नहीं?").blocked  # whether, not how


def test_meaning_of_gmp_is_explained_but_using_it_to_decide_is_not() -> None:
    assert not check_advice("What does GMP mean?").blocked
    assert not check_advice("GMP ka matlab kya hota hai?").blocked
    assert check_advice("Is the GMP high enough that I should apply?").blocked
    assert check_advice("What is the GMP today?").blocked  # a live premium is a price cue
    assert check_advice("GMP dekh ke apply karna chahiye kya?").blocked


def test_sounds_evaluative_but_is_a_fact() -> None:
    for question in (
        "Is there any pending litigation against the promoters?",
        "What risks does the company list in the prospectus?",
        "Is the company profitable as per the restated financials?",
        "Does the company receive any money from the offer for sale?",
        "Is this IPO only an offer for sale?",
        "Minimum kitne shares ke liye apply kar sakte hai?",
    ):
        assert not check_advice(question).blocked, question
