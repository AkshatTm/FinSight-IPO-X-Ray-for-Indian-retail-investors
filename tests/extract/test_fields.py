from pathlib import Path

import pytest

from finsight.core.schemas import FieldSpec
from finsight.evaluate.gold import DEFAULT_DOC, FIELDS
from finsight.extract import field_ids, get_field, load_fields


def test_registry_has_the_eleven_gold_fields_with_matching_types_and_docs() -> None:
    fields = load_fields()
    assert [f.id for f in fields] == list(FIELDS)
    for f in fields:
        assert f.type == FIELDS[f.id]
        assert f.doc == DEFAULT_DOC[f.id]
        assert f.label_en
        assert f.label_hi
        assert f.questions
        assert f.sections


def test_ladder_flags_follow_adr_023() -> None:
    not_on_ladder = {f.id for f in load_fields() if not f.ladder}
    assert not_on_ladder == {"offer_price", "price_band", "objects_of_offer"}


def test_objects_use_the_table_extractor_and_the_rest_use_rules() -> None:
    by_id = {f.id: f for f in load_fields()}
    assert by_id["objects_of_offer"].extractor == "table"
    # ADR-018 (G2): rules first on every field; the fine-tuned model is the cross-check
    assert all(f.extractor == "rules" for i, f in by_id.items() if i != "objects_of_offer")
    assert {f.fallback for f in by_id.values() if f.ladder} == {"qa_finetuned"}
    assert by_id["offer_price"].fallback is None  # rules-only, Prospectus cover


def test_get_field_and_field_ids() -> None:
    assert isinstance(get_field("registrar"), FieldSpec)
    assert field_ids() == list(FIELDS)
    with pytest.raises(KeyError, match="nope"):
        get_field("nope")


def test_load_rejects_duplicates_and_unknown_docs(tmp_path: Path) -> None:
    bad = tmp_path / "f.yaml"
    entry = (
        "  - {id: a, label_en: A, label_hi: ए, type: text, doc: rhp, sections: [cover],"
        " questions: [q], extractor: rules}\n"
    )
    bad.write_text("fields:\n" + entry + entry, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_fields(bad)
    bad.write_text("fields:\n" + entry.replace("doc: rhp", "doc: annual_report"), encoding="utf-8")
    with pytest.raises(ValueError, match="doc"):
        load_fields(bad)
