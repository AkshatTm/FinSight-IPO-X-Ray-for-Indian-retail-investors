"""Third retrieval nudge (P3.6): use-of-money questions pull in the objects passages."""

from pathlib import Path

import pytest

from finsight.core.schemas import Passage
from finsight.retrieve.boost import OBJECTS_EXTRA, inject, objects_candidates, wants_objects


def passage(page: int, section: str, doc: str = "rhp", k: int = 0) -> Passage:
    return Passage(
        id=f"i:p{page}:c{k}", ipo_id="i", doc_type=doc, section_id=section, page_start=page,
        page_end=page, text="x", char_to_bbox=[],
    )  # fmt: skip


@pytest.mark.parametrize(
    "question",
    [
        "How will the money from the IPO be used?",
        "What are the objects of the offer?",
        "Where will the proceeds go?",
        "What is the use of proceeds?",
        "इस आईपीओ का पैसा कहाँ लगेगा?",
        "पैसे का उपयोग कैसे होगा?",
        "paisa kahan lagega",
        "paise kis kaam mein lagenge",
    ],
)
def test_use_of_money_questions(question: str) -> None:
    assert wants_objects(question)


@pytest.mark.parametrize(
    "question",
    [
        "Who is the registrar?",
        "What is the face value?",
        "प्रमोटर कौन हैं?",
        "Is the fresh issue Rs 800 lakh?",
    ],
)
def test_other_questions_untouched(question: str) -> None:
    assert not wants_objects(question)


def test_objects_candidates_rhp_first_in_page_order_and_capped() -> None:
    ps = [passage(300, "x")] + [passage(200 + i, "objects_of_the_offer", k=i) for i in range(6)]
    ps.append(passage(150, "objects_of_the_offer", doc="prospectus"))
    got = objects_candidates(ps)
    assert len(got) == OBJECTS_EXTRA
    assert [ps[i].doc_type for i in got] == ["rhp"] * OBJECTS_EXTRA
    assert [ps[i].page_start for i in got] == sorted(ps[i].page_start for i in got)


def test_inject_appends_objects_passages_after_the_pool() -> None:
    ps = [passage(10 + i, "other") for i in range(5)] + [passage(171, "objects_of_the_offer")]
    order = [(i, 5.0 - i) for i in range(5)]
    out = inject("How will the money be used?", ps, order, pool=3)
    assert [i for i, _ in out] == [0, 1, 2, 5]
    assert inject("Who is the registrar?", ps, order, pool=3)[-1][0] != 5


def test_inject_does_not_duplicate_a_passage_already_in_the_pool() -> None:
    ps = [passage(171, "objects_of_the_offer"), passage(5, "other")]
    out = inject("paisa kahan lagega", ps, [(0, 3.0), (1, 1.0)], pool=2)
    assert [i for i, _ in out] == [0, 1]


@pytest.mark.skipif(
    not Path("data/processed/ather-energy-2025/index").exists(), reason="needs the built index"
)
@pytest.mark.parametrize("ipo", ["ather-energy-2025", "urban-company-2025"])
@pytest.mark.parametrize(
    "question", ["How will the money from the IPO be used?", "paisa kahan lagega"]
)
def test_real_indexes_return_an_objects_passage_in_the_top_five(ipo: str, question: str) -> None:
    from finsight.core.config import get_settings
    from finsight.retrieve import Retriever

    s = get_settings()
    r = Retriever(s.paths.processed_dir, pool=s.retrieve.rerank_top_n, top_k=s.retrieve.final_top_k)
    hits = r.search(question, ipo).hits
    assert any(h.passage.section_id == "objects_of_the_offer" for h in hits)
