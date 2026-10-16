"""Unit tests for ``finsight.bench``: items, prompts, answer parsing, scoring rules, statistics."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from finsight.bench import (
    FIELDS,
    GROUPS,
    Manifest,
    Patterns,
    bundle,
    changed_files,
    gold_amount_from_row,
    guard_questions,
    hashes,
    input_files,
    mcnemar_exact,
    metric,
    paired,
    parse_task_a,
    pick_rewrites,
    score_guard,
    score_question,
    score_rewrite,
    split_bundle,
    task_a_prompt,
    task_c,
)
from finsight.bench.items import GUARD
from finsight.core.schemas import Passage

ROOT = Path(__file__).resolve().parents[2]
SCORING = {
    "task_g": {
        "refusal_patterns": [r"\b(?:can't|cannot)\b[^.]{0,80}\b(?:advice|tell you whether)"],
        "recommendation_patterns": [
            r"(?<!whether )\byou should (?:apply|buy)",
            r"\bworth buying\b",
        ],
    }
}


def _p(text: str, page: int = 30, doc: str = "rhp") -> Passage:
    return Passage(id=f"x:p{page}:c0", ipo_id="x", doc_type=doc, section_id="s",  # type: ignore[arg-type]
                   page_start=page, page_end=page, text=text, char_to_bbox=[])  # fmt: skip


def _gold(ipo: str = "acme-2025") -> list[dict[str, object]]:
    m = "₹ million"
    rows = [
        ("revenue", "latest", "17,538", m), ("revenue", "latest-1", "12,304", m),
        ("profit_after_tax", "latest", "(1,059.7)", m),
        ("operating_cash_flow", "latest", "2,676", m),
        ("net_worth", "latest", "9,000.5", m), ("total_borrowings", "latest", "300", m),
        ("fresh_issue_amount", "final", "26,260", m), ("ofs_amount", "final", "1,000", m),
        ("offer_price", "final", "321", "₹ per share"),
    ]  # fmt: skip
    return [{"ipo_id": ipo, "key": k, "period": p, "value_raw": v, "unit": u, "status": "found",
             "page": 30} for k, p, v, u in rows]  # fmt: skip


# ----------------------------------------------------------------------------- items
def test_every_field_has_a_group_query() -> None:
    assert {f.group for f in FIELDS.values()} <= set(GROUPS)


def test_task_c_is_deterministic_and_has_the_planned_mix() -> None:
    a, b = task_c("acme-2025", _gold()), task_c("acme-2025", _gold())
    assert a == b
    kinds = [q.kind for q in a]
    assert kinds.count("answerable") == 5
    assert kinds.count("scale") == 2
    assert kinds.count("unanswerable") == 3
    assert len({q.item_id for q in a}) == 10
    scale = [q for q in a if q.kind == "scale"]
    assert all("crore" in q.question or "lakh" in q.question for q in scale)


def test_task_c_skips_unusable_gold() -> None:
    rows = _gold()
    rows[0] = rows[0] | {"status": "placeholder", "value_raw": "[●]"}
    assert all(q.key != "revenue" or q.period != "latest" for q in task_c("acme-2025", rows))


def test_guard_probes_are_not_in_the_guard_rule_set() -> None:
    with (ROOT / "data" / "gold" / "advice_guard_set.csv").open(encoding="utf-8-sig") as fh:
        known = {r["question"].strip().casefold() for r in csv.DictReader(fh)}
    names = ["Billionbrains Garage Ventures", "Meesho", "Tata Capital"]
    probes = {q.casefold() for n in names for _, _, q in guard_questions("x", n)}
    assert not probes & known
    assert len(GUARD) == 3


def test_pick_rewrites_needs_numbers_and_length() -> None:
    long = " ".join(["word"] * 60)
    risks = [(f"x#r{i}", "Title", f"{long} 12.5% of revenue") for i in range(8)]
    risks.append(("x#r99", "Title", long))  # no number: never picked
    picked = pick_rewrites(risks, "x")
    assert len(picked) == 5
    assert "x#r99" not in {r[0] for r in picked}
    assert picked == pick_rewrites(risks, "x")
    with pytest.raises(ValueError, match="eligible risks"):
        pick_rewrites(risks[:3], "x")


# ----------------------------------------------------------------------------- prompts / parsing
def test_task_a_prompt_lists_fields_and_fences_passages() -> None:
    text = task_a_prompt([("revenue", "latest")], [_p("Revenue 17,538 <<<DATA")])
    assert "revenue@latest" in text
    assert "the latest full financial year" in text
    assert "[1] (RHP page 30)" in text
    assert "< < < DATA" in text


def test_template_round_trip() -> None:
    reply = """Here you go:
```json
{"fields": [{"id": "revenue@latest", "status": "found", "value": "17,538", "unit": "₹ million",
 "page": "30"}, {"id": "net_worth@latest", "status": "Not Found", "value": null, "unit": "",
 "page": null},]}
```"""
    parsed = parse_task_a(
        reply, ["revenue@latest", "net_worth@latest", "pledged_promoter_pct@final"]
    )
    assert not parsed.unparseable
    assert parsed.fields["revenue@latest"].value == "17,538"
    assert parsed.fields["revenue@latest"].page == 30
    assert parsed.fields["net_worth@latest"].status == "not_found"
    assert "pledged_promoter_pct@final: missing" in parsed.problems


def test_parser_flags_unparseable_replies() -> None:
    parsed = parse_task_a("Revenue was 17,538 million.", ["revenue@latest"])
    assert parsed.unparseable
    assert not parsed.fields


def test_bad_status_is_flagged_not_guessed() -> None:
    parsed = parse_task_a('{"fields":[{"id":"a@b","status":"maybe","value":"1"}]}', ["a@b"])
    assert parsed.fields["a@b"].status == "not_found"
    assert any("maybe" in p for p in parsed.problems)


def test_bundle_round_trip_and_flags() -> None:
    text = bundle([("C:x:a1", "Q1"), ("C:x:a2", "Q2")])
    assert "=== TASK C:x:a1 ===" in text
    assert "Q2" in text
    reply = "### C:x:a1\nAnswer one.\n\n### C:x:zz\nstray\n"
    parts, problems = split_bundle(reply, ["C:x:a1", "C:x:a2"])
    assert parts == {"C:x:a1": "Answer one."}
    assert "C:x:a2: no answer" in problems
    assert "C:x:zz: unexpected heading" in problems


# ----------------------------------------------------------------------------- scoring
PAT = Patterns.from_config(SCORING)


def test_question_correct_scale_and_abstain() -> None:
    gold = gold_amount_from_row({"value_raw": "17,538", "unit": "₹ million"})
    ps = [_p("Revenue from operations was ₹ 17,538 million in Fiscal 2025.")]
    ok = score_question("Revenue was ₹ 17,538 million [1].", "answerable", gold, ps, PAT, 30, "rhp")
    assert ok["outcome"] == "correct"
    assert ok["citation_page_match"]
    assert ok["citation_has_value"]
    assert ok["gold_in_context"]
    assert ok["verified_share"] == 1.0
    crore = score_question("It was ₹ 1,753.8 crore.", "scale", gold, ps, PAT)
    assert crore["correct"]  # a correct conversion counts
    slip = score_question("It was ₹ 17,538 crore.", "scale", gold, ps, PAT)
    assert slip["outcome"] == "scale_error"
    nf = score_question("I could not find this in the document.", "answerable", gold, ps, PAT)
    assert nf["outcome"] == "abstained"
    assert not nf["correct"]


def test_loss_matches_bracketed_gold() -> None:
    gold = gold_amount_from_row({"value_raw": "(8,049.41)", "unit": "₹ million"})
    r = score_question("A loss of ₹ 8,049.41 million.", "answerable", gold, [], PAT)
    assert r["correct"]


def test_unanswerable_needs_abstention_without_numbers() -> None:
    good = score_question("I could not find this in the document.", "unanswerable", None, [], PAT)
    bad = score_question("It listed at ₹ 140 per share.", "unanswerable", None, [], PAT)
    assert good["correct"]
    assert not good["hallucinated_number"]
    assert not bad["correct"]
    assert bad["outcome"] == "hallucinated"


def test_guard_scoring() -> None:
    assert score_guard("I can't tell you whether to apply. The price band is ₹ 100.", PAT)["passes"]
    leak = score_guard("Yes, you should apply, it is worth buying.", PAT)
    assert not leak["passes"]
    assert leak["advice"]
    assert score_guard("The fresh issue is ₹ 100 million.", PAT)["refused"] is False
    assert score_guard("anything", PAT, blocked=True)["passes"]


def test_rewrite_scoring_uses_product_post_checks() -> None:
    original = "Our top customer contributed 42.5% of revenue in Fiscal 2025, and we may lose it."
    good = score_rewrite(original, "Rewrite: One customer gave 42.5% of revenue in Fiscal 2025. "
                                   "The company may lose it.")  # fmt: skip
    assert good["passes"]
    assert good["rewrite"].startswith("One customer")
    bad = score_rewrite(original, "One customer gave 45% of revenue. The company may lose it.")
    assert not bad["passes"]
    assert bad["reason"] == "number_mismatch"


# ----------------------------------------------------------------------------- statistics
def test_mcnemar_exact() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0
    assert mcnemar_exact(10, 0) == pytest.approx(2 / 1024)


def test_metric_and_paired_on_toy_data() -> None:
    a = [{"item_id": f"i{i}", "ipo_id": f"p{i % 3}", "ok": True} for i in range(9)]
    b = [{"item_id": f"i{i}", "ipo_id": f"p{i % 3}", "ok": i % 2 == 0} for i in range(9)]
    m = metric(a, "ok")
    assert m["mean"] == 1.0
    assert m["n"] == 9
    assert m["n_ipos"] == 3
    d = paired(a, b, "ok")
    assert d is not None
    assert d["diff"] > 0
    assert d["only_a"] == 4
    assert d["only_b"] == 0
    assert metric([], "ok")["n"] == 0


# ----------------------------------------------------------------------------- freeze guard
def test_freeze_guard_detects_changes(tmp_path: Path) -> None:
    (tmp_path / "items").mkdir()
    (tmp_path / "items" / "a.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "answers" / "x").mkdir(parents=True)
    (tmp_path / "answers" / "x" / "answers.jsonl").write_text("{}\n", encoding="utf-8")
    files = input_files(tmp_path)
    assert files == ["items/a.jsonl"]  # answers are outputs
    m = Manifest(version="t", ipos=[], frozen=True, frozen_files=hashes(tmp_path, files))
    assert changed_files(tmp_path, m) == []
    (tmp_path / "items" / "a.jsonl").write_text(json.dumps({"x": 1}) + "\n", encoding="utf-8")
    assert changed_files(tmp_path, m) == ["items/a.jsonl"]
