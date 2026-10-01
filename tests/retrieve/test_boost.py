import pytest

from finsight.core.schemas import Passage
from finsight.retrieve.boost import (
    COVER_EXTRA,
    cover_candidates,
    inject,
    prefers_prospectus,
    prospectus_first,
    wants_cover,
)
from finsight.retrieve.retriever import IpoIndex, Retriever


def passage(doc: str, page: int, text: str = "x", k: int = 0) -> Passage:
    return Passage(
        id=f"i:p{page}:c{k}",
        ipo_id="i",
        doc_type=doc,
        section_id="s",
        page_start=page,
        page_end=page,
        text=text,
        char_to_bbox=[],
    )


@pytest.mark.parametrize(
    "question",
    [
        "Who is the registrar to the offer?",
        "What is the total size of this IPO?",
        "What is the face value of each equity share?",
        "इस IPO का रजिस्ट्रार कौन है?",
        "IPO में एक शेयर किस भाव पर मिला?",
        "kaun hain book running lead managers",
    ],
)
def test_cover_questions(question):
    assert wants_cover(question)


@pytest.mark.parametrize(
    "question", ["What are the risk factors?", "How many employees does it have?", "मुकदमे कौन से हैं?"]
)
def test_body_questions_untouched(question):
    assert not wants_cover(question)
    assert not prefers_prospectus(question)


def test_only_price_questions_prefer_prospectus():
    assert prefers_prospectus("At what price were shares allotted in the IPO?")
    assert prefers_prospectus("What is the offer price?")
    assert not prefers_prospectus("Who is the registrar?")


def test_cover_candidates_are_first_pages_preferred_doc_first():
    ps = [passage("rhp", 1), passage("prospectus", 1), passage("rhp", 40), passage("prospectus", 2)]
    assert cover_candidates(ps, prefer_prospectus=True) == [1, 3, 0]
    assert cover_candidates(ps) == [0, 1, 3]


def test_cover_candidates_are_capped():
    ps = [passage("rhp", 1, k=k) for k in range(10)]
    assert len(cover_candidates(ps)) == COVER_EXTRA


def test_inject_adds_cover_after_pool_and_skips_when_not_asked():
    ps = [passage("rhp", 50), passage("rhp", 60), passage("rhp", 1)]
    order = [(0, 0.9), (1, 0.5)]
    assert [i for i, _ in inject("Who is the registrar?", ps, order, pool=2)] == [0, 1, 2]
    assert inject("What are the risks?", ps, order, pool=2) == order
    assert inject("What are the risks?", ps, order, pool=1) == order[:1]


def test_inject_does_not_duplicate():
    ps = [passage("rhp", 1), passage("rhp", 60)]
    order = [(0, 0.9), (1, 0.5)]
    assert inject("Who is the registrar?", ps, order, pool=2) == order


def test_prospectus_first_is_stable_and_price_only():
    ps = [passage("rhp", 5), passage("prospectus", 6), passage("rhp", 7), passage("prospectus", 8)]
    order = [(0, 4.0), (1, 3.0), (2, 2.0), (3, 1.0)]
    got = prospectus_first("What is the offer price?", ps, order)
    assert [i for i, _ in got] == [1, 3, 0, 2]
    assert prospectus_first("Who is the registrar?", ps, order) == order


def test_retriever_puts_cover_in_reach_for_bm25_only():
    ps = [passage("rhp", 80, "registrar registrar registrar", k=i) for i in range(6)]
    ps.append(passage("rhp", 2, "Registrar: KFin Technologies"))
    r = Retriever(top_k=3, pool=3)
    r.add("i", IpoIndex(ps))
    pages = [h.passage.page_start for h in r.search("Who is the registrar?", "i").hits]
    assert 2 in pages


@pytest.mark.parametrize(
    "question",
    [
        "इस ऑफ़र का रजिस्ट्रार कौन है?",
        "रजिस्ट्रार कौन है",
        "फ्रेश इश्यू का आकार कितना है?",
        "प्रत्येक इक्विटी शेयर का अंकित मूल्य (फेस वैल्यू) कितना है?",
        "फेस वैल्यू क्या है",
        "प्रमोटर कौन हैं?",
        "इस IPO के लीड मैनेजर कौन हैं",
        "ऑफ़र प्राइस कितना है?",
        "ऑफर प्राइस क्या है",
        "कुल इश्यू साइज़ कितना है?",
        "कुल इश्यू कितना है",
        "registrar kaun hai",
        "fresh issue kitna hai",
        "face value kya hai",
        "promoter kaun hain",
        "lead manager kaun hain",
        "offer price kya hai",
        "kul issue kitna hai",
        "IPO ka kul size kya hai",
    ],
)
def test_hindi_and_hinglish_cover_cues(question):
    assert wants_cover(question)


@pytest.mark.parametrize(
    "question",
    [
        "कंपनी का राजस्व कितना है?",
        "company ke risk factors kya hain",
        "How many employees does the company have?",
    ],
)
def test_other_questions_do_not_pull_the_cover(question):
    assert not wants_cover(question)


def test_nukta_spellings_are_the_same_word():
    assert wants_cover("ऑफ\u093cर प्राइस")
    assert wants_cover("ऑफर प्राइस")
    assert prefers_prospectus("ऑफ\u093cर प्राइस कितना है?")
    assert prefers_prospectus("ऑफर प्राइस कितना है?")
