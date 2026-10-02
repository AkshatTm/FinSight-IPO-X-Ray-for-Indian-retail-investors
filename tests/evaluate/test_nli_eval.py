import json
from pathlib import Path

from finsight.evaluate.nli_eval import build_items, run, summarise

SPLITS = {"a": "dev", "b": "test", "c": "test"}


def gold_row(ipo: str, field: str, value: object, quote: str) -> dict[str, object]:
    return {"ipo_id": ipo, "field_id": field, "doc": "rhp", "status": "present",
            "value_raw": value, "quote": quote}  # fmt: skip


GOLD = [
    gold_row("a", "registrar", "Alpha Registrar Limited", "REGISTRAR Alpha Registrar Limited"),
    gold_row("a", "promoters", ["P One", "P Two"], "PROMOTERS P One and P Two"),
    gold_row("b", "registrar", "Beta Registrar Limited", "REGISTRAR Beta Registrar Limited"),
    gold_row("b", "promoters", ["Q One"], "PROMOTERS Q One"),
    gold_row("c", "registrar", "Gamma Registrar Limited", "REGISTRAR Gamma Registrar Limited"),
]


def test_each_field_gets_an_entailed_a_contradicted_and_a_neutral_item_per_language() -> None:
    items = build_items(GOLD, SPLITS)
    a_registrar = [i for i in items if i["ipo_id"] == "a" and i["field"] == "registrar"]
    assert {(i["language"], i["label"]) for i in a_registrar} == {
        (lang, lab) for lang in ("en", "hi") for lab in ("entailed", "contradicted", "neutral")
    }
    entailed = next(i for i in a_registrar if i["label"] == "entailed" and i["language"] == "en")
    assert "Alpha Registrar Limited" in entailed["hypothesis"]
    wrong = next(i for i in a_registrar if i["label"] == "contradicted" and i["language"] == "en")
    assert "Alpha" not in wrong["hypothesis"]  # a name from another IPO
    neutral = next(i for i in a_registrar if i["label"] == "neutral" and i["language"] == "en")
    assert "P One" in neutral["hypothesis"]  # a promoter claim against a registrar quote


def test_the_item_without_a_partner_field_has_no_neutral_item() -> None:
    items = build_items(GOLD, SPLITS)
    c = [i for i in items if i["ipo_id"] == "c"]
    assert {i["label"] for i in c} == {"entailed", "contradicted"}  # c has no promoters row


def test_scores_are_split_into_dev_then_test_with_intervals(tmp_path: Path) -> None:
    gold = tmp_path / "gold.jsonl"
    gold.write_text("\n".join(json.dumps(r) for r in GOLD), encoding="utf-8")
    cfg = tmp_path / "ipos.yaml"
    rows = "".join(f"  - {{ipo_id: {k}, split: {v}}}" + chr(10) for k, v in SPLITS.items())
    cfg.write_text("ipos:" + chr(10) + rows, encoding="utf-8")

    def oracle(premise: str, hypothesis: str) -> dict[str, float]:
        # right on everything except neutral claims, which it calls entailed
        if "promoter" in hypothesis and "REGISTRAR" in premise:
            return {"entailed": 0.9, "neutral": 0.1}
        if "Registrar" in hypothesis and premise.split()[1] not in hypothesis:
            return {"contradicted": 0.9, "neutral": 0.1}
        return {"entailed": 0.9, "neutral": 0.1}

    result = run(gold, cfg, oracle, 0.5)
    dev = result["dev"]
    assert dev["accuracy"]["n"] == 12  # ipo a: registrar and promoters, 3 labels x 2 languages
    assert 0 < dev["accuracy"]["rate"] < 1
    assert dev["recall_by_label"]["neutral"]["rate"] == 0.0
    assert summarise([])["dev"]["accuracy"]["n"] == 0
