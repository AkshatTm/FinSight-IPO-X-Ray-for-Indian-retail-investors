import random

from finsight.core.schemas import Passage
from finsight.evaluate.seeded_errors import (
    ERROR_TYPES,
    EXPECTED,
    build_items,
    change_digit,
    load_bases,
    report,
    rounded,
    run_item,
    scale_lakh_crore,
    scale_million_crore,
    show,
    summarise,
)
from finsight.normalize import parse_amount
from finsight.verify import same_value


def passage(ipo: str, doc: str, page: int, text: str) -> Passage:
    return Passage(
        id=f"{ipo}:{doc}:p{page}:c0", ipo_id=ipo, doc_type=doc, section_id="cover",  # type: ignore[arg-type]
        page_start=page, page_end=page, text=text, char_to_bbox=[],
    )  # fmt: skip


def gold(ipo: str, field: str, doc: str, raw: str, page: int = 3, status: str = "present") -> dict:
    return {"ipo_id": ipo, "field_id": field, "doc": doc, "value_raw": raw, "page": page,
            "status": status}  # fmt: skip


def cover(total: str, fresh: str, ofs: str, price: str) -> str:
    return (
        f"INITIAL PUBLIC OFFERING OF EQUITY SHARES OF FACE VALUE OF ₹ 1 EACH FOR CASH AT A PRICE "
        f"OF ₹ {price} PER EQUITY SHARE AGGREGATING UP TO ₹ {total} MILLION (THE “OFFER”). THE "
        f"OFFER COMPRISES A FRESH ISSUE AGGREGATING UP TO ₹ {fresh} MILLION AND AN OFFER FOR SALE "
        f"OF 11,051,746 EQUITY SHARES AGGREGATING UP TO ₹ {ofs} MILLION."
    )


IPOS = {
    "acme-2025": ("29,808", "26,260", "3,548", "321"),
    "bolt-2025": ("54,211.87", "42,500.00", "11,711.87", "111"),
    "core-2025": ("87,500", "60,000", "27,500", "708"),
}
PASSAGES = {ipo: [passage(ipo, "prospectus", 3, cover(*v))] for ipo, v in IPOS.items()}
SPLITS = {"acme-2025": "dev", "bolt-2025": "test", "core-2025": "test"}
GOLD = [
    row
    for ipo, (total, fresh, ofs, price) in IPOS.items()
    for row in (
        gold(ipo, "total_issue_size", "prospectus", f"₹ {total} MILLION"),
        gold(ipo, "fresh_issue_size", "prospectus", f"₹ {fresh} MILLION"),
        gold(ipo, "ofs_amount", "prospectus", f"₹ {ofs} MILLION"),
        gold(ipo, "ofs_shares", "prospectus", "11,051,746 EQUITY SHARES"),
        gold(ipo, "offer_price", "prospectus", f"₹ {price}"),
        gold(ipo, "face_value", "prospectus", "₹ 1"),
        gold(ipo, "price_band", "rhp", "₹ [●]", status="placeholder"),
        gold(ipo, "registrar", "rhp", "KFin Technologies Limited"),
    )
]


def test_bases_are_gold_values_a_real_passage_states() -> None:
    bases, skipped = load_bases(GOLD, PASSAGES, SPLITS)
    assert len(bases) == 18  # 6 numeric fields x 3 IPOs; blanks and names are left out
    assert skipped == []
    assert {b.split for b in bases if b.ipo_id == "acme-2025"} == {"dev"}
    missing = [*GOLD, gold("acme-2025", "ofs_amount", "prospectus", "₹ 9,999 MILLION", page=9)]
    bases, skipped = load_bases(missing[-1:], PASSAGES, SPLITS)
    assert bases == []
    assert "no passage on the gold page" in skipped[0]


def test_values_are_written_as_an_answer_would_print_them() -> None:
    assert show(parse_amount("₹26,260 MILLION")) == "₹ 26,260 million"  # type: ignore[arg-type]
    assert show(parse_amount("₹10,600.00 MILLION")) == "₹ 10,600.00 million"  # type: ignore[arg-type]
    assert show(parse_amount("11,051,746 EQUITY SHARES")) == "11,051,746 equity shares"  # type: ignore[arg-type]
    assert show(parse_amount("₹ 321")) == "₹ 321"  # type: ignore[arg-type]


def test_each_corruption_does_what_its_name_says() -> None:
    value = parse_amount("₹ 26,260 million")
    assert value is not None
    assert scale_lakh_crore(value) == "₹ 2,626.0 lakh"  # the crore figure, 100x too small
    assert scale_million_crore(value) == "₹ 26,260 crore"  # same digits, 10x too big
    assert rounded(value) == "₹ 2,626 crore"
    assert same_value(parse_amount(rounded(value) or ""), value)  # type: ignore[arg-type]
    changed = change_digit(value, random.Random(1))
    assert changed is not None
    assert changed != show(value)
    assert sum(a != b for a, b in zip(changed, show(value), strict=True)) == 1
    price = parse_amount("₹ 321")
    assert price is not None
    assert scale_lakh_crore(price) is None  # no scale word: nothing to slip
    assert rounded(price) is None


def test_items_are_balanced_reproducible_and_cover_both_languages() -> None:
    bases, _ = load_bases(GOLD, PASSAGES, SPLITS)
    items = build_items(bases)
    assert [(i.kind, i.answer) for i in items] == [(i.kind, i.answer) for i in build_items(bases)]
    kinds = {k: [i for i in items if i.kind == k] for k in (*ERROR_TYPES, "correct")}
    assert all(kinds[k] for k in kinds)
    assert all(len(kinds[k]) <= 20 for k in ERROR_TYPES)
    assert {i.language for i in items} == {"en", "hi"}
    for item in kinds["invented"]:
        assert item.target == 1  # the invented number is the second one in the answer
    for item in kinds["swap_metric"]:
        assert item.evidence  # the swapped value comes from the same IPO's passages


def test_the_verifier_catches_every_seeded_error_on_clean_passages() -> None:
    bases, _ = load_bases(GOLD, PASSAGES, SPLITS)
    rows = [run_item(i) for i in build_items(bases)]
    summary = summarise(rows)
    assert summary["detection"]["rate"] == 1.0
    assert summary["false_alarm"]["hits"] == 0
    assert summary["scale_mismatch_recall"]["rate"] == 1.0
    for row in rows:
        assert row["expected"] == EXPECTED[row["kind"]]
        assert row["exact"], row


def test_summary_counts_detection_and_false_alarms_separately() -> None:
    rows = [
        {"kind": "digit", "ok": True, "exact": True, "got": "wrong_value"},
        {"kind": "scale_lakh_crore", "ok": True, "exact": False, "got": "wrong_value"},
        {"kind": "invented", "ok": False, "exact": False, "got": "verified"},
        {"kind": "correct", "ok": True, "exact": True, "got": "verified"},
        {"kind": "rounding_ok", "ok": False, "exact": False, "got": "wrong_value"},
    ]
    s = summarise(rows)
    assert (s["detection"]["hits"], s["detection"]["n"]) == (2, 3)
    assert (s["scale_mismatch_recall"]["hits"], s["scale_mismatch_recall"]["n"]) == (0, 1)
    assert (s["false_alarm"]["hits"], s["false_alarm"]["n"]) == (1, 2)
    assert s["per_type"]["digit"] == {"n": 1, "ok": 1, "exact": 1, "got": {"wrong_value": 1}}


def test_the_headline_is_the_held_out_run_with_the_fix_beside_it() -> None:
    bases, skipped = load_bases(GOLD, PASSAGES, SPLITS)
    rows = [run_item(i) for i in build_items(bases)]
    result = report(rows, skipped, len(bases))
    assert result["benchmark_level"] == "unit"
    scale = result["headline"]["scale_mismatch_recall"]
    assert (scale["held_out"]["hits"], scale["held_out"]["n"]) == (35, 40)
    assert scale["held_out"]["rate"] == 0.875
    assert scale["held_out"]["wilson_95"][0] < 0.875 < scale["held_out"]["wilson_95"][1]
    by_split = scale["held_out"]["by_split"]
    assert (by_split["dev"]["hits"], by_split["test"]["hits"], by_split["test"]["n"]) == (
        13,
        22,
        27,
    )
    assert scale["after_one_rule_fix"] == result["metrics"]["scale_mismatch_recall"]
    assert set(result["headline"]) >= {"detection", "exact_reason", "false_alarm", "labels"}
    assert "not held-out" in result["headline"]["labels"]["after_one_rule_fix"]
    assert "unit-level" in result["notes"]
    assert "35/40" in result["notes"]
