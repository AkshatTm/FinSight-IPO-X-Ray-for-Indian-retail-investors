from finsight.core.schemas import Passage
from finsight.verify.nli import check_claims, decide, premise_for


def passage(text: str, n: int = 1) -> Passage:
    return Passage(
        id=f"x:p{n}:c0", ipo_id="x", doc_type="rhp", section_id="s", page_start=n, page_end=n,
        text=text, char_to_bbox=[],
    )  # fmt: skip


def fixed(label: str, p: float = 0.9):  # type: ignore[no-untyped-def]
    def scorer(premise: str, hypothesis: str) -> dict[str, float]:
        scorer.calls.append((premise, hypothesis))  # type: ignore[attr-defined]
        return {label: p, "neutral": 1 - p}

    scorer.calls = []  # type: ignore[attr-defined]
    return scorer


def test_a_label_needs_enough_probability_or_the_claim_stays_unverifiable() -> None:
    assert decide({"entailed": 0.9, "neutral": 0.1}) == ("entailed", 0.9)
    assert decide({"contradicted": 0.8, "neutral": 0.2}) == ("contradicted", 0.8)
    assert decide({"entailed": 0.4, "contradicted": 0.35, "neutral": 0.25})[0] == "neutral"


def test_only_sentences_without_numbers_are_checked() -> None:
    ps = [passage("Kotak is a lead manager."), passage("The issue is Rs. 500 million.", 2)]
    scorer = fixed("entailed")
    out = check_claims(
        "Kotak is a book running lead manager [1]. The issue is Rs. 500 million [2].", ps, scorer
    )
    assert [c.sentence for c in out] == ["Kotak is a book running lead manager."]
    assert out[0].label == "entailed"
    assert out[0].cited == [1]
    assert scorer.calls[0][0] == "Kotak is a lead manager."  # premise = the cited passage


def test_not_found_and_tiny_sentences_are_skipped() -> None:
    ps = [passage("text")]
    assert check_claims("I could not find this in the document.", ps, fixed("entailed")) == []
    assert check_claims("मुझे यह जानकारी दस्तावेज़ में नहीं मिली।", ps, fixed("entailed")) == []
    assert check_claims("Yes [1].", ps, fixed("entailed")) == []


def test_without_a_citation_the_best_passages_are_the_premise() -> None:
    ps = [passage(f"passage {i}", i) for i in range(1, 6)]
    assert premise_for([], ps) == "passage 1 passage 2 passage 3"
    assert premise_for([2, 9], ps) == "passage 2"  # an out-of-range marker is ignored
