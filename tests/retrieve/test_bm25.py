from finsight.retrieve.bm25 import BM25Index, tokenize

TEXTS = [
    "The fresh issue is up to 4,720 million equity shares of face value 10",
    "KFin Technologies Limited is the Registrar to the Offer",
    "The BRLMs are Axis Capital and JM Financial",
    "Risk factors relating to our business and industry",
]


def test_tokenize_drops_number_commas_stopwords_and_case() -> None:
    assert tokenize("The Fresh Issue of ₹ 4,720.50 million") == [
        "fresh",
        "issue",
        "4720.50",
        "million",
    ]
    assert tokenize("1,23,456") == ["123456"]  # Indian digit grouping too


def test_exact_token_finds_its_passage() -> None:
    index = BM25Index(TEXTS)
    assert index.search("who is the registrar", k=3)[0][0] == 1
    assert index.search("KFin", k=3)[0][0] == 1
    assert index.search("4720", k=3)[0][0] == 0  # question without the comma matches the passage


def test_scores_are_best_first_and_unrelated_passages_are_left_out() -> None:
    hits = BM25Index(TEXTS).search("BRLMs Axis Capital", k=4)
    assert hits[0][0] == 2
    assert [h[1] for h in hits] == sorted((h[1] for h in hits), reverse=True)
    assert all(score > 0 for _, score in hits)
    assert BM25Index(TEXTS).search("zebra", k=4) == []


def test_empty_index_and_empty_query() -> None:
    assert BM25Index([]).search("anything") == []
    assert BM25Index(TEXTS).search("the of") == []  # only stop words
    assert BM25Index(["", "..."]).search("x") == []  # passages with no tokens do not crash


def test_k_caps_results() -> None:
    assert len(BM25Index(TEXTS).search("the issue business", k=2)) <= 2
