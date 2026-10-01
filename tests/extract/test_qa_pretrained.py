"""QA extractor tests use a fake answerer, so no model is loaded. A slow test loads the real one."""

import pytest

from finsight.core.schemas import (
    Count,
    ListValue,
    Money,
    Page,
    ParsedDoc,
    Placeholder,
    Range,
    TextValue,
)
from finsight.extract import QAExtractor, RawAnswer, build_passages
from finsight.extract import get_field as deployed_field


def get_field(field_id: str):  # type: ignore[no-untyped-def]
    """The field as if it named the pretrained model, whatever fields.yaml says today."""
    spec = deployed_field(field_id)
    return spec.model_copy(update={"extractor": "rules", "fallback": "qa_pretrained"})


def make_doc(pages: list[str], doc_type: str = "rhp") -> ParsedDoc:
    return ParsedDoc(
        ipo_id="urban-company-2025", doc_type=doc_type, source_path="x.pdf", n_pages=len(pages),
        sha256="0", pages=[
            Page(number=i, width=595, height=842, words=[], text=t, is_scanned=False)
            for i, t in enumerate(pages, 1)
        ],
    )  # type: ignore[arg-type]  # fmt: skip


def answerer_for(answer: str, score: float = 0.9, only_page_with: str | None = None):  # type: ignore[no-untyped-def]
    def answer_fn(question: str, contexts: list[str]) -> list[RawAnswer | None]:
        out: list[RawAnswer | None] = []
        for ctx in contexts:
            start = ctx.find(answer)
            if start < 0 or (only_page_with and only_page_with not in ctx):
                out.append(None)
            else:
                out.append(
                    RawAnswer(text=answer, score=score, start=start, end=start + len(answer))
                )
        return out

    return answer_fn


def run(field_id: str, pages: list[str], answer: str, **kw):  # type: ignore[no-untyped-def]
    qa = QAExtractor(answerer=answerer_for(answer, **kw))
    return qa.extract(make_doc(pages), [], [], get_field(field_id))


def test_passages_are_cut_at_sentence_ends_and_carry_ids_and_pages() -> None:
    text = "First sentence here. " * 100  # about 2,100 characters
    doc = make_doc([text, "Short page."])
    passages = build_passages(doc, [], get_field("face_value"), max_chars=800)
    assert len(passages) >= 3
    assert all(len(p.text) <= 800 for p in passages)
    assert passages[0].id == "urban-company-2025:p1:c0"
    assert passages[0].page == 1
    assert passages[-1].page == 2
    pro = build_passages(make_doc(["Hello."], "prospectus"), [], get_field("face_value"))
    assert pro[0].id == "urban-company-2025:prospectus:p1:c0"


def test_passages_respect_the_field_sections_and_a_cap() -> None:
    doc = make_doc(["page"] * 30)
    cover_only = build_passages(doc, [], get_field("registrar"))  # cover = first 15 pages
    assert {p.page for p in cover_only} == set(range(1, 16))
    capped = build_passages(doc, [], get_field("registrar"), max_passages=4)
    assert len(capped) == 4


def test_money_answer_is_read_with_its_unit_from_the_context() -> None:
    pages = ["A fresh issue aggregating up to ₹ 4,720 million by our Company"]
    (cand,) = run("fresh_issue_size", pages, "4,720")[:1]
    assert isinstance(cand.value, Money)
    assert cand.value.value_inr == 4_720_000_000
    assert cand.extractor == "qa_pretrained"
    assert cand.page == 1
    assert cand.passage_id == "urban-company-2025:p1:c0"
    assert cand.score == pytest.approx(0.9)


def test_placeholder_count_text_and_list_and_range_answers() -> None:
    blank = run("ofs_amount", ["aggregating up to ₹ [●] million"], "₹ [●] million")
    assert isinstance(blank[0].value, Placeholder)
    shares = run("ofs_shares", ["offer for sale of 11,051,746 Equity Shares of"], "11,051,746")
    assert isinstance(shares[0].value, Count)
    assert shares[0].value.value == 11_051_746
    name = run(
        "registrar",
        ["Registrar to the Offer KFin Technologies Limited"],
        "KFin Technologies Limited",
    )
    assert isinstance(name[0].value, TextValue)
    people = run("promoters", ["Promoters: A B, C D and E F"], "A B, C D and E F")
    assert isinstance(people[0].value, ListValue)
    assert people[0].value.items == ["A B", "C D", "E F"]
    band = run("price_band", ["Price Band: ₹ 440 to ₹ 463 per share"], "₹ 440 to ₹ 463")
    assert isinstance(band[0].value, Range)


def test_unreadable_low_score_or_empty_answers_are_dropped() -> None:
    assert run("fresh_issue_size", ["The price is about four thousand"], "four thousand") == []
    assert run("face_value", ["face value ₹ 1 each"], "₹ 1", score=0.01) == []
    assert (
        QAExtractor(answerer=lambda q, c: [None] * len(c)).extract(
            make_doc(["x"]), [], [], get_field("face_value")
        )
        == []
    )


def test_only_fields_that_use_qa_are_run() -> None:
    qa = QAExtractor(answerer=answerer_for("₹ 321"))  # the fields as fields.yaml has them today
    assert qa.extract(make_doc(["price of ₹ 321"]), [], [], deployed_field("offer_price")) == []
    assert qa.extract(make_doc(["capex ₹ 321"]), [], [], deployed_field("objects_of_offer")) == []


def test_best_answers_first_and_one_candidate_per_distinct_value() -> None:
    pages = ["face value of ₹ 1 each", "face value of ₹ 1 each again", "face value of ₹ 10 each"]

    def answers(question: str, contexts: list[str]) -> list[RawAnswer | None]:
        out: list[RawAnswer | None] = []
        for n, ctx in enumerate(contexts):
            token = "₹ 10" if "₹ 10" in ctx else "₹ 1"
            i = ctx.find(token)
            out.append(RawAnswer(text=token, score=0.9 - 0.1 * n, start=i, end=i + len(token)))
        return out

    cands = QAExtractor(answerer=answers, top_k=3).extract(
        make_doc(pages), [], [], get_field("face_value")
    )
    assert [c.value.value_inr for c in cands] == [1, 10]  # type: ignore[union-attr]
    assert cands[0].score > cands[1].score


@pytest.mark.slow
def test_real_model_reads_a_cover_sentence() -> None:
    from finsight.extract.qa_pretrained import default_answerer

    qa = QAExtractor(answerer=default_answerer())
    doc = make_doc(
        [
            "The Offer comprises a Fresh Issue of [●] Equity Shares aggregating up to "
            "₹ 4,720 million by our Company."
        ]
    )
    cands = qa.extract(doc, [], [], get_field("fresh_issue_size"))
    assert cands
    assert isinstance(cands[0].value, Money)
    assert cands[0].value.value_inr == 4_720_000_000
