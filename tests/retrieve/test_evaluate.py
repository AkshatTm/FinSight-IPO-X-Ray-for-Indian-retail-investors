import json
from pathlib import Path

import pytest

from finsight.core.schemas import Passage
from finsight.retrieve.evaluate import (
    Question,
    evaluate,
    is_hit,
    load_questions,
    reciprocal_rank,
    score_method,
    tune_threshold,
)
from finsight.retrieve.retriever import Hit, IpoIndex, Retriever


def passage(page: int, text: str = "t", end: int | None = None, ipo: str = "a-2025") -> Passage:
    return Passage(
        id=f"{ipo}:p{page}:c0", ipo_id=ipo, doc_type="rhp", section_id="s",
        page_start=page, page_end=end or page, text=text, char_to_bbox=[],
    )  # fmt: skip


def hit(page: int, rank: int, score: float = 1.0, **kw: object) -> Hit:
    return Hit(passage=passage(page, **kw), score=score, rank=rank)  # type: ignore[arg-type]


def question(
    page: int | None = 3, answerable: bool = True, lang: str = "en", ipo: str = "a-2025"
) -> Question:
    return Question(
        ipo_id=ipo, question="q", language=lang, evidence_page=page, answerable=answerable  # type: ignore[arg-type]
    )  # fmt: skip


def test_is_hit_uses_page_range_and_ipo() -> None:
    q = question(3)
    assert is_hit(hit(3, 1), q)
    assert is_hit(hit(2, 1, end=4), q)  # a table passage spanning pages 2-4
    assert not is_hit(hit(4, 1), q)
    assert not is_hit(hit(3, 1, ipo="b-2025"), q)


def test_reciprocal_rank() -> None:
    q = question(3)
    assert reciprocal_rank([hit(9, 1), hit(3, 2)], q) == 0.5
    assert reciprocal_rank([hit(9, 1)], q) == 0.0


def test_tune_threshold_separates_answerable_from_unanswerable() -> None:
    scored = [(True, 5.0), (True, 4.0), (True, 3.0), (False, 1.0), (False, 0.5), (False, None)]
    t = tune_threshold(scored)
    assert t is not None
    assert 1.0 < t <= 3.0  # keeps every answerable, abstains on every unanswerable


def test_tune_threshold_prefers_lower_on_ties_and_needs_both_kinds() -> None:
    t = tune_threshold([(True, 5.0), (False, 5.0)])
    assert t is not None
    assert t <= 5.0
    assert tune_threshold([(True, 1.0), (True, 2.0)]) is None
    assert tune_threshold([(False, 1.0)]) is None


def test_score_method_recall_mrr_and_language_split() -> None:
    ranked = [
        (question(3, ipo="a-2025"), [hit(3, 1, ipo="a-2025")]),
        (question(3, ipo="a-2025", lang="hi"), [hit(9, 1, ipo="a-2025"), hit(3, 2, ipo="a-2025")]),
        (question(5, ipo="b-2025"), [hit(5, 1, ipo="b-2025")]),
        (question(None, answerable=False, ipo="b-2025"), [hit(1, 1, ipo="b-2025")]),
    ]
    out = score_method(ranked)
    assert out["all"]["n"] == 3  # type: ignore[index]  # the unanswerable question is not scored
    assert out["all"]["recall@1"]["mean"] == pytest.approx(2 / 3, abs=1e-3)  # type: ignore[index]
    assert out["all"]["recall@5"]["mean"] == 1.0  # type: ignore[index]
    assert out["hi"]["n"] == 1  # type: ignore[index]
    assert out["hi"]["mrr"]["mean"] == 0.5  # type: ignore[index]


def test_load_questions_validates(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    good = {"ipo_id": "a-2025", "question": "q", "language": "en", "answer_gold": "x",
            "evidence_page": 3, "answerable": True}  # fmt: skip
    path.write_text(json.dumps(good) + "\n", encoding="utf-8")
    assert load_questions(path)[0].evidence_page == 3
    path.write_text(json.dumps({**good, "evidence_page": None}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="evidence_page"):
        load_questions(path)
    with pytest.raises(FileNotFoundError, match="Akshat"):
        load_questions(tmp_path / "missing.jsonl")


def test_evaluate_end_to_end_with_bm25_and_dev_only_threshold() -> None:
    passages = [
        passage(1, "KFin Technologies is the registrar"),
        passage(2, "Axis Capital is the BRLM"),
        passage(3, "risk factors"),
    ]
    r = Retriever(top_k=5)
    r.add("a-2025", IpoIndex(passages))
    search = {
        "bm25": lambda q: (lambda res: (res.hits, res.top_score))(r.search(q.question, q.ipo_id))
    }

    def q(text: str, page: int | None, answerable: bool) -> Question:
        return Question(ipo_id="a-2025", question=text, language="en", evidence_page=page,
                        answerable=answerable)  # fmt: skip

    dev = [
        q("registrar kfin", 1, True),
        q("BRLM axis capital", 2, True),
        q("zebra stripes", None, False),
    ]
    test = [q("who is the registrar kfin", 1, True), q("zebra", None, False)]
    report = evaluate(dev, test, search)
    method = report["methods"]["bm25"]  # type: ignore[index]
    assert method["test"]["all"]["recall@1"]["mean"] == 1.0
    assert method["abstain"]["test_unanswerable_abstained"] == "1/1"
    assert method["abstain"]["test_answerable_wrongly_abstained"] == "0/1"
    assert report["thresholds"]["bm25"] is not None  # type: ignore[index]
