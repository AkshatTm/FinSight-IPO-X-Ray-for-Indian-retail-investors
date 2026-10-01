import json
from pathlib import Path

import pytest
from weaklabel_docs import CAPITAL, COVER, FILLER, OFFER, acme, sections_for

from finsight.extract import get_field
from finsight.ingest.corpus import CorpusDoc, CorpusPage
from finsight.weaklabel import (
    build_dataset,
    clean_text,
    find_answer,
    find_seeds,
    negatives,
    propagate,
    sample_audit,
    score_audit,
    split_by_ipo,
    to_squad,
)


def fresh_examples():  # type: ignore[no-untyped-def]
    doc, sections = acme()
    field = get_field("fresh_issue_size")
    seed = find_seeds(doc, sections).seeds[field.id]
    pos = propagate(doc, sections, field, seed)
    return doc, sections, field, seed, pos


def test_negatives_are_one_to_two_per_positive_and_never_hold_the_value() -> None:
    doc, sections, field, seed, pos = fresh_examples()
    neg = negatives(doc, sections, field, seed, pos)
    assert len(pos) <= len(neg) <= 2 * len(pos)
    for e in neg:
        assert e.is_impossible
        assert e.answer_text == ""
        assert find_answer(field, seed.value, e.context) is None
        assert e.passage_id not in {p.passage_id for p in pos}


def test_negatives_are_deterministic() -> None:
    doc, sections, field, seed, pos = fresh_examples()
    first = negatives(doc, sections, field, seed, pos)
    assert first == negatives(doc, sections, field, seed, pos)


def test_squad_v2_record() -> None:
    _, _, field, _, pos = fresh_examples()
    row = to_squad(pos[0], field.questions[0])
    assert set(row) == {"id", "ipo_id", "field_id", "title", "question", "context", "answers"}
    assert row["answers"]["text"] == [pos[0].answer_text]
    assert row["answers"]["answer_start"] == [pos[0].answer_start]
    doc, sections, field, seed, pos = fresh_examples()
    neg = to_squad(negatives(doc, sections, field, seed, pos)[0], "q?")
    assert neg["answers"] == {"text": [], "answer_start": []}


def test_split_is_by_ipo_disjoint_and_repeatable() -> None:
    ipos = [f"ipo-{i}" for i in range(50)]
    train, dev = split_by_ipo(ipos)
    assert not train & dev
    assert train | dev == set(ipos)
    assert len(dev) == 5
    assert (train, dev) == split_by_ipo(list(reversed(ipos)))


def corpus_file(folder: Path, ipo_id: str, company: str, pages: list[str]) -> None:
    doc = CorpusDoc(
        ipo_id=ipo_id, mapping_key=ipo_id, company=company, close_year=2019,
        doc_kind="prospectus", source_file="x.json", n_pages=len(pages),
        pages=[CorpusPage(number=i, text=t) for i, t in enumerate(pages, 1)],
        sections=sections_for(len(pages)), key_sections_found=True,
    )  # fmt: skip
    (folder / f"{ipo_id}.json").write_text(doc.model_dump_json(), encoding="utf-8")


def test_build_dataset_end_to_end_without_demo_leakage(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    pages = [COVER] + [FILLER] * 17 + [OFFER, CAPITAL, FILLER]
    for i in range(12):
        corpus_file(corpus, f"acme{i}-2019", f"Acme {i} Limited", pages)
    corpus_file(corpus, "urban-company-2021", "Urban Company Limited", pages)  # a demo name
    out = tmp_path / "weaklabel"
    stats = build_dataset(corpus, out, excel={}, excluded=["Urban Company Limited"])
    rows = [
        json.loads(line)
        for name in ("train.jsonl", "dev.jsonl")
        for line in (out / name).read_text(encoding="utf-8").splitlines()
    ]
    assert rows
    assert not any(r["ipo_id"].startswith("urban-company") for r in rows)
    assert stats["excluded_ipos"] == ["urban-company-2021"]
    assert stats["n_ipos"] == 12
    assert stats["seed_coverage"]["fresh_issue_size"] == "12/12"
    train_ipos = {r["ipo_id"] for r in rows[: stats["train"]["examples"]]}
    dev_ipos = {r["ipo_id"] for r in rows[stats["train"]["examples"] :]}
    assert not train_ipos & dev_ipos
    per_field = stats["per_field"]["fresh_issue_size"]
    assert per_field["positives"] > 0
    assert per_field["negatives"] >= per_field["positives"]
    for r in rows:
        if r["answers"]["text"]:
            start = r["answers"]["answer_start"][0]
            assert r["context"][start:].startswith(r["answers"]["text"][0])


def test_audit_sample_is_stratified_and_highlights_the_answer(tmp_path: Path) -> None:
    rows = []
    for field_id, n in [("fresh_issue_size", 80), ("registrar", 30), ("face_value", 2)]:
        for i in range(n):
            context = f"text before ANSWER{i} after"
            rows.append({
                "id": f"{field_id}-{i}", "ipo_id": f"ipo-{i % 7}", "field_id": field_id,
                "title": "t", "question": "q?", "context": context,
                "answers": {"text": [f"ANSWER{i}"], "answer_start": [context.index("ANSWER")]},
            })  # fmt: skip
    sample = sample_audit(rows, n=50)
    assert len(sample) == 50
    counts = {
        f: sum(r["field_id"] == f for r in sample)
        for f in ("fresh_issue_size", "registrar", "face_value")
    }
    assert counts["face_value"] == 2  # all there are
    assert counts["registrar"] >= 10
    assert counts["fresh_issue_size"] > counts["registrar"]
    assert all("«" in r["passage"] and "»" in r["passage"] for r in sample)
    assert all(r["label"] == "" for r in sample)
    assert sample == sample_audit(rows, n=50)  # repeatable
    assert all(r["answers"]["text"] for r in sample)  # positives only


def test_corpus_text_gets_its_rupee_sign_and_blanks_back() -> None:
    assert clean_text("aggregating ` 200,000 and `5") == "aggregating ₹ 200,000 and ₹5"
    assert clean_text("at Rs. [] per share, [ ] million") == "at Rs. [●] per share, [●] million"
    assert clean_text("the `Issue` term") == "the `Issue` term"  # quotes stay


def test_audit_never_exceeds_n_when_many_fields_are_present() -> None:
    rows = [
        {"id": f"{f}-{i}", "ipo_id": "x", "field_id": f, "title": "t", "question": "q?",
         "context": "a ANSWER b", "answers": {"text": ["ANSWER"], "answer_start": [2]}}
        for f in [f"field{k}" for k in range(8)]
        for i in range(30)
    ]  # fmt: skip
    sample = sample_audit(rows, n=50)
    assert len(sample) == 50
    assert min(sum(r["field_id"] == f"field{k}" for r in sample) for k in range(8)) >= 6


def test_audit_score_is_precision_with_a_wilson_interval() -> None:
    rows = [{"field_id": "face_value", "label": "correct"}] * 45
    rows += [{"field_id": "face_value", "label": "wrong_value"}] * 2
    rows += [{"field_id": "promoters", "label": "wrong_span", "label_source": "x"}] * 3
    score = score_audit(rows)
    assert (score["n"], score["correct"], score["precision"]) == (50, 45, 0.9)
    assert score["wilson_95"] == [0.7864, 0.9565]
    assert score["labels"] == {"correct": 45, "wrong_span": 3, "wrong_value": 2, "ambiguous": 0}
    assert score["per_field"]["promoters"]["wrong_span"] == 3
    assert score["label_sources"] == ["hand", "x"]


def test_audit_score_rejects_an_unfilled_or_unknown_label() -> None:
    with pytest.raises(ValueError, match="audit labels"):
        score_audit([{"field_id": "face_value", "label": ""}])
