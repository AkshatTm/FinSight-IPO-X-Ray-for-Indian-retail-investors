from finsight.verify import find_metrics, metric_at, split_claims
from finsight.verify.claims import sentence_spans


def raws(answer: str) -> list[list[str]]:
    return [[n.amount.raw for n in c.numbers] for c in split_claims(answer)]


def test_sentences_end_at_stops_and_keep_their_trailing_citations() -> None:
    answer = "The fresh issue is ₹ 300 crore. [1] The registrar is KFin Technologies Limited [2]."
    claims = split_claims(answer, n_passages=3)
    assert [c.claim.sentence for c in claims] == [
        "The fresh issue is ₹ 300 crore. [1]",
        "The registrar is KFin Technologies Limited [2].",
    ]
    assert [c.claim.cited for c in claims] == [[1], [2]]
    for c in claims:
        lo, hi = c.claim.char_span
        assert answer[lo:hi] == c.claim.sentence


def test_abbreviations_and_decimals_do_not_end_a_sentence() -> None:
    answer = "The issue is Rs. 300 crore at 12.5% for M. Kumar. The band is ₹ 304 to ₹ 321 [2]."
    assert len(sentence_spans(answer)) == 2
    assert raws(answer) == [["Rs. 300 crore", "12.5%"], ["₹ 304 to ₹ 321"]]


def test_years_pages_and_citation_markers_are_not_numbers() -> None:
    answer = "In 2025 the company filed its RHP (page 34) [2][3]. It was founded in 2013 [12]."
    claims = split_claims(answer, n_passages=3)
    assert [c.numbers for c in claims] == [[], []]
    assert [c.claim.cited for c in claims] == [[2, 3], []]  # [12] points at no passage


def test_number_spans_index_the_answer() -> None:
    answer = "Total ₹ 29,808 million [1]. Fresh issue ₹26,260 million and 11,051,746 equity shares."
    for c in split_claims(answer):
        for n in c.numbers:
            assert answer[n.start : n.end] == n.amount.raw
        assert c.claim.amounts == [n.amount for n in c.numbers]
    assert raws(answer) == [["₹ 29,808 million"], ["₹26,260 million", "11,051,746 equity shares"]]


def test_hindi_answer_uses_the_same_path() -> None:
    answer = "फ्रेश इश्यू का आकार ₹ 26,260 मिलियन है [1]। ऑफर फॉर सेल 1,10,51,746 इक्विटी शेयर का है [2]।"
    claims = split_claims(answer, n_passages=2)
    assert len(claims) == 2
    assert [c.claim.cited for c in claims] == [[1], [2]]
    first, second = claims[0].numbers[0].amount, claims[1].numbers[0].amount
    assert (first.kind, first.scale_word) == ("money", "million")  # type: ignore[union-attr]
    assert (second.kind, second.value) == ("count", 11051746)  # type: ignore[union-attr]


def test_an_answer_without_text_has_no_claims() -> None:
    assert split_claims("") == []
    assert split_claims("  \n ") == []


# ---- metric keywords ---------------------------------------------------------------------

COVER = (
    "INITIAL PUBLIC OFFERING OF UP TO [●] EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH AGGREGATING "
    "UP TO ₹[●] MILLION COMPRISING A FRESH ISSUE OF UP TO [●] EQUITY SHARES OF FACE VALUE OF "
    "₹ 1 EACH AGGREGATING UP TO ₹26,260 MILLION AND AN OFFER FOR SALE OF UP TO 11,051,746 "
    "EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH AGGREGATING UP TO ₹[●] MILLION"
)


def metric_of(text: str, needle: str, nth: int = 0) -> str | None:
    from finsight.normalize import parse_amounts

    spans = parse_amounts(text)
    where = [(s.start, s.end) for s in spans]
    span = [s for s in spans if s.amount.raw == needle][nth]
    return metric_at(text, span.start, span.end, where)


def test_the_metric_named_before_the_amount_wins() -> None:
    assert metric_of(COVER, "₹26,260 MILLION") == "fresh_issue"
    assert metric_of(COVER, "11,051,746 EQUITY SHARES") == "ofs"
    assert metric_of(COVER, "₹[●] MILLION", 0) == "total_issue"
    assert metric_of(COVER, "₹[●] MILLION", 1) == "ofs"
    assert metric_of(COVER, "₹ 1", 1) == "face_value"  # per-share keyword: the next amount only


def test_keywords_in_english_hindi_and_hinglish() -> None:
    cases = {
        "The fresh issue size is ₹ 300 crore": "fresh_issue",
        "OFS ka size ₹ 300 crore hai": "ofs",
        "फ्रेश इश्यू का आकार ₹ 300 करोड़ है": "fresh_issue",
        "ऑफर फॉर सेल ₹ 300 करोड़ का है": "ofs",
        "कुल इश्यू ₹ 300 करोड़ का है": "total_issue",
        "The total offer size is ₹ 300 crore": "total_issue",
        "प्राइस बैंड ₹ 304 से ₹ 321 है": "price_band",
        "The offer price is ₹ 321 per share": "offer_price",
        "अंकित मूल्य ₹ 1 है": "face_value",
        "Revenue from operations was ₹ 300 crore": "revenue",
        "The company made a loss of ₹ 300 crore": "profit",
        "It raised ₹ 300 crore": None,
    }
    for text, expected in cases.items():
        raw = next(r for r in ("₹ 300 crore", "₹ 300 करोड़", "₹ 304 से ₹ 321", "₹ 321", "₹ 1")
                   if r in text)  # fmt: skip
        assert metric_of(text, raw) == expected, text


def test_a_keyword_right_after_the_amount_counts_when_none_precedes() -> None:
    assert metric_of("₹ 10 is the face value of each share", "₹ 10") == "face_value"
    text = "Revenue grew. ₹ 300 crore was raised."
    assert metric_of(text, "₹ 300 crore") is None  # the keyword is in another sentence


def test_overlapping_keywords_keep_the_earlier_one() -> None:
    assert [h.metric for h in find_metrics("the fresh issue size")] == ["fresh_issue"]
    assert [h.metric for h in find_metrics("total issue size and offer for sale")] == [
        "total_issue",
        "ofs",
    ]


PROSPECTUS = (
    "INITIAL PUBLIC OFFERING OF 92,867,945 EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH FOR CASH AT A "
    "PRICE OF ₹ 321 ^ PER EQUITY SHARE INCLUDING A SECURITIES PREMIUM OF ₹ 320 ^ PER EQUITY SHARE "
    "(THE “OFFER PRICE”) AGGREGATING UP TO ₹ 29,808 MILLION *^ (THE “OFFER”). THE OFFER COMPRISES "
    "A FRESH ISSUE OF 81,816,199 EQUITY SHARES AGGREGATING UP TO ₹ 26,260 MILLION (THE “FRESH "
    "ISSUE”) AND AN OFFER FOR SALE OF 11,051,746 EQUITY SHARES AGGREGATING UP TO ₹ 3,548 MILLION."
)


def test_a_defined_term_after_the_amount_names_it() -> None:
    assert metric_of(PROSPECTUS, "₹ 321") == "offer_price"  # "at a price of"
    assert metric_of(PROSPECTUS, "₹ 320") == "premium"
    assert metric_of(PROSPECTUS, "₹ 29,808 MILLION") == "total_issue"  # (THE "OFFER")
    assert metric_of(PROSPECTUS, "₹ 26,260 MILLION") == "fresh_issue"
    assert metric_of(PROSPECTUS, "₹ 3,548 MILLION") == "ofs"


def test_a_pure_offer_for_sale_total_carries_both_metrics() -> None:
    from finsight.normalize import parse_amounts
    from finsight.verify import MetricIndex

    text = (
        "INITIAL PUBLIC OFFERING THROUGH AN OFFER FOR SALE OF 123,587,570 EQUITY SHARES "
        "AGGREGATING UP TO ₹ 87,500 MILLION (THE “OFFER”)."
    )
    spans = parse_amounts(text)
    index = MetricIndex(text, [(s.start, s.end) for s in spans])
    money = next(s for s in spans if s.amount.kind == "money")
    assert set(index.at(money.start, money.end)) == {"total_issue", "ofs"}
