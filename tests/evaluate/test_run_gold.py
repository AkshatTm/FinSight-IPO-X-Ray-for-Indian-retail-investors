"""The gold runner on a tiny made-up document: no model, no data folder."""

from typing import Any

import pytest

from finsight.core.schemas import (
    Count,
    ListValue,
    Money,
    Page,
    ParsedDoc,
    Placeholder,
    Section,
    TextValue,
)
from finsight.evaluate.run_gold import (
    cached,
    gold_text,
    gold_value,
    ladder_rows,
    mask_cover,
    run_document,
    stated_in_body,
    summarise,
)
from finsight.extract import FineTunedExtractor, QAExtractor, RawAnswer, get_field, load_fields
from finsight.extract.qa_finetuned import weights_dir

COVER = "FRESH ISSUE OF UP TO 81,816,199 EQUITY SHARES AGGREGATING UP TO ₹26,260 MILLION"
BODY = (
    "The Fresh Issue aggregates up to ₹ 26,260 million. "
    "The Registrar to the Offer is KFin Technologies Limited."
)


def doc(pages: list[str]) -> ParsedDoc:
    return ParsedDoc(
        ipo_id="acme-2025", doc_type="rhp", source_path="x.pdf", n_pages=len(pages), sha256="0",
        pages=[Page(number=i, width=1, height=1, words=[], text=t, is_scanned=False)
               for i, t in enumerate(pages, 1)],
    )  # type: ignore[arg-type]  # fmt: skip


def section(section_id: str) -> Section:
    return Section(
        id=section_id, title=section_id, start_page=16, end_page=16, method="toc", confidence=1.0
    )


def row(field_id: str, value: Any, status: str = "present") -> dict[str, Any]:
    return {"ipo_id": "acme-2025", "field_id": field_id, "doc": "rhp", "value_raw": value,
            "status": status, "page": 1}  # fmt: skip


def finder(answer: str, score: float = 0.9):  # type: ignore[no-untyped-def]
    def fn(question: str, contexts: list[str]) -> list[RawAnswer | None]:
        out: list[RawAnswer | None] = []
        for ctx in contexts:
            at = ctx.find(answer)
            out.append(RawAnswer(answer, score, at, at + len(answer)) if at >= 0 else None)
        return out

    return fn


def test_gold_values_are_typed_by_field_and_status() -> None:
    money = gold_value(row("fresh_issue_size", "₹26,260 MILLION"), get_field("fresh_issue_size"))
    assert isinstance(money, Money)
    count = gold_value(row("ofs_shares", "11,051,746 EQUITY SHARES"), get_field("ofs_shares"))
    assert isinstance(count, Count)
    assert isinstance(
        gold_value(row("ofs_amount", "₹[●] MILLION", "placeholder"), get_field("ofs_amount")),
        Placeholder,
    )
    assert (
        gold_value(row("fresh_issue_size", None, "not_in_document"), get_field("fresh_issue_size"))
        is None
    )
    assert gold_value(row("registrar", "KFin"), get_field("registrar")) == TextValue(text="KFin")
    names = gold_value(row("promoters", ["A B", "C D"]), get_field("promoters"))
    assert names == ListValue(items=["A B", "C D"])
    assert gold_text(row("promoters", ["A B", "C D"])) == "A B; C D"
    assert gold_text(row("x", None, "not_in_document")) == ""


def test_ladder_rows_keep_ladder_fields_in_their_own_document() -> None:
    fields = load_fields()
    gold = [
        row("fresh_issue_size", "₹ 1 MILLION"),
        row("price_band", "₹[●]", "placeholder"),  # not a ladder field
        {**row("total_issue_size", "₹ 2 MILLION"), "doc": "prospectus"},
        {**row("total_issue_size", "₹ 2 MILLION"), "doc": "rhp"},  # wrong document for the field
    ]
    kept = ladder_rows(gold, fields)
    assert [(r["field_id"], r["doc"]) for r in kept] == [
        ("fresh_issue_size", "rhp"),
        ("total_issue_size", "prospectus"),
    ]


def test_mask_cover_blanks_the_first_pages_only() -> None:
    pages = ["cover text"] + ["body"] * 20
    masked = mask_cover(doc(pages), pages=15)
    assert [p.text for p in masked.pages[:15]] == [""] * 15
    assert masked.pages[15].text == "body"
    assert doc(pages).pages[0].text == "cover text"  # the original is untouched


def test_stated_in_body_checks_the_pages_the_extractor_may_read() -> None:
    pages = [COVER] + [""] * 14 + [BODY]
    masked = mask_cover(doc(pages))
    fresh, registrar = get_field("fresh_issue_size"), get_field("registrar")
    offer = [section("the_offer"), section("general_information")]
    # without a section only the (blanked) cover pages are searched: nothing to read
    assert not stated_in_body(row("fresh_issue_size", "₹26,260 MILLION"), fresh, masked, [])
    assert stated_in_body(
        row("fresh_issue_size", "₹ 2,626 CRORE"), fresh, masked, offer
    )  # same money
    assert not stated_in_body(row("fresh_issue_size", "₹ 9,999 MILLION"), fresh, masked, offer)
    # registrar, managers and promoters are read from the cover only (fields.yaml)
    kfin = row("registrar", "KFin Technologies Limited")
    assert not stated_in_body(kfin, registrar, masked, offer)
    face = row("face_value", "₹ 1")
    assert not stated_in_body(face, get_field("face_value"), masked, [section("capital_structure")])
    blank = row("ofs_amount", "₹[●] MILLION", "placeholder")
    assert not stated_in_body(blank, get_field("ofs_amount"), masked, offer)  # body has no [●]
    assert stated_in_body(row("fresh_issue_size", None, "not_in_document"), fresh, masked, [])


def test_run_document_scores_both_settings_and_masks_the_cover() -> None:
    pages = [COVER] + [""] * 14 + [BODY]
    sections = [
        Section(
            id="the_offer",
            title="The Offer",
            start_page=16,
            end_page=16,
            method="toc",
            confidence=1.0,
        )
    ]
    fields = {f.id: f for f in load_fields()}
    qa = QAExtractor(answerer=finder("₹26,260 MILLION"))
    gold = [row("fresh_issue_size", "₹26,260 MILLION")]
    out = run_document(qa, gold, fields, doc(pages), sections)
    assert out[0]["full"]["nvm"] is True
    assert out[0]["full"]["pred_page"] == 1
    # the body repeats the value as "₹ 26,260 million", which this answerer cannot find
    assert out[0]["in_body"] is True
    assert out[0]["body_only"]["nvm"] is False
    assert out[0]["body_only"]["pred_raw"] == ""

    qa2 = QAExtractor(answerer=finder("₹ 26,260 million"))
    out2 = run_document(qa2, gold, fields, doc(pages), sections)
    assert out2[0]["body_only"]["nvm"] is True
    assert out2[0]["body_only"]["pred_page"] == 16


def test_no_answer_matches_only_not_in_document() -> None:
    fields = {f.id: f for f in load_fields()}
    qa = QAExtractor(answerer=finder("nothing like this"))
    gold = [
        row("fresh_issue_size", None, "not_in_document"),
        row("fresh_issue_size", "₹26,260 MILLION"),
    ]
    out = run_document(qa, gold, fields, doc([COVER]), [])
    assert [o["full"]["nvm"] for o in out] == [True, False]
    assert out[0]["full"]["em"] is True  # "" against ""


def test_cached_answerer_asks_each_passage_once() -> None:
    calls: list[list[str]] = []

    def base(question: str, contexts: list[str]) -> list[RawAnswer | None]:
        calls.append(list(contexts))
        return [RawAnswer(c[:1], 0.5, 0, 1) for c in contexts]

    ask = cached(base)
    first = ask("q", ["a", "b", "a"])
    second = ask("q", ["b", "c"])
    assert [r.text for r in first if r] == ["a", "b", "a"]
    assert [r.text for r in second if r] == ["b", "c"]
    assert calls == [["a", "b"], ["c"]]
    ask("other question", ["a"])
    assert calls[-1] == ["a"]  # the question is part of the key


def test_summary_counts_per_split_setting_and_field() -> None:
    def pred(ok: bool) -> dict[str, Any]:
        return {"nvm": ok, "em": ok, "f1": 1.0 if ok else 0.0, "pred_raw": "x" if ok else ""}

    preds = [
        {
            "ipo_id": "a",
            "field_id": "f1",
            "in_body": True,
            "full": pred(True),
            "body_only": pred(False),
        },
        {"ipo_id": "a", "field_id": "f2", "in_body": False, "full": pred(True), "body_only": None},
        {
            "ipo_id": "b",
            "field_id": "f1",
            "in_body": True,
            "full": pred(False),
            "body_only": pred(True),
        },
    ]
    s = summarise(preds, {"a": "dev", "b": "test"})
    assert s["metrics"]["dev"]["full"]["n"] == 2
    assert s["metrics"]["dev"]["full"]["nvm"] == 1.0
    assert s["metrics"]["dev"]["body_only"]["n"] == 1  # only rows whose value is in the body
    assert s["metrics"]["test"]["full"]["nvm"] == 0.0
    assert s["metrics"]["test"]["body_only"]["nvm"] == 1.0
    assert s["per_field"]["dev"]["f1"]["full"]["n"] == 1


def test_finetuned_extractor_reads_its_seed_folder_and_reports_missing_weights(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assert weights_dir(13, tmp_path) == tmp_path / "extractor" / "seed-13"
    ft = FineTunedExtractor(42, models_dir=tmp_path)
    assert ft.name == "qa_finetuned"
    with pytest.raises(FileNotFoundError, match="fetch 42"):
        ft.extract(
            doc([COVER]),
            [],
            [],
            get_field("fresh_issue_size").model_copy(update={"fallback": "qa_finetuned"}),
        )
    ok = FineTunedExtractor(13, answerer=finder("₹26,260 MILLION"), models_dir=tmp_path)
    found = ok.extract(
        doc([COVER]),
        [],
        [],
        get_field("fresh_issue_size").model_copy(update={"fallback": "qa_finetuned"}),
    )
    assert found
    assert found[0].extractor == "qa_finetuned"
    # a field that does not name the extractor is left alone
    spec = get_field("fresh_issue_size").model_copy(
        update={"extractor": "rules", "fallback": "qa_pretrained"}
    )
    assert ok.extract(doc([COVER]), [], [], spec) == []
