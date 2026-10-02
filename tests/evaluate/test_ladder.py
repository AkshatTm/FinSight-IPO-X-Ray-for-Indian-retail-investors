"""The ladder table from synthetic result files: shape, intervals, paired differences, choice."""

import copy
import csv
import json
from pathlib import Path
from typing import Any

import pytest

from finsight.evaluate.ladder import (
    build,
    choose_extractors,
    load_results,
    per_row_scores,
    rung_summary,
    write_all,
)

IPOS = {"d1": "dev", "d2": "dev", "t1": "test", "t2": "test", "t3": "test"}
FIELDS = ("fresh_issue_size", "registrar")


def pred(ok: bool) -> dict[str, Any]:
    return {"nvm": ok, "em": ok, "f1": 1.0 if ok else 0.0, "pred_raw": "x" if ok else ""}


def result(name: str, wins: set[tuple[str, str]], seed: int | None = None) -> dict[str, Any]:
    """A result file where the (ipo, field) pairs in ``wins`` are right in both settings."""
    rows = []
    for ipo in IPOS:
        for field in FIELDS:
            in_body = field == "fresh_issue_size"  # the registrar is read from the cover only
            rows.append(
                {
                    "ipo_id": ipo,
                    "field_id": field,
                    "full": pred((ipo, field) in wins),
                    "in_body": in_body,
                    "body_only": pred((ipo, field) in wins and ipo != "t3") if in_body else None,
                }
            )
    return {
        "name": name,
        "seed": seed,
        "git_sha": "abc1234",
        "data": {
            "gold_version": "v1",
            "splits": {
                "dev": [i for i, s in IPOS.items() if s == "dev"],
                "test": [i for i, s in IPOS.items() if s == "test"],
            },
        },
        "predictions": rows,
    }


ALL = {(i, f) for i in IPOS for f in FIELDS}


def write_results(tmp_path: Path) -> Path:
    ladder = tmp_path / "ladder"
    ladder.mkdir()
    files = {
        "rules": result(
            "rules", {(i, f) for i, f in ALL if f == "registrar"} | {("d1", "fresh_issue_size")}
        ),
        "qa_pretrained": result("qa_pretrained", {("t1", "fresh_issue_size")}),
        "qa_finetuned_seed13": result("qa_finetuned_seed13", ALL, 13),
        "qa_finetuned_seed42": result("qa_finetuned_seed42", ALL, 42),
        "qa_finetuned_seed2026": result("qa_finetuned_seed2026", ALL - {("t2", "registrar")}, 2026),
    }
    for name, content in files.items():
        (ladder / f"{name}.json").write_text(json.dumps(content), encoding="utf-8")
    return ladder


def test_missing_result_files_are_named(tmp_path: Path) -> None:
    ladder = write_results(tmp_path)
    (ladder / "qa_finetuned_seed42.json").unlink()
    with pytest.raises(FileNotFoundError, match=r"qa_finetuned_seed42\.json"):
        load_results(ladder)


def test_fine_tuned_rows_average_over_seeds_and_body_only_keeps_body_rows(tmp_path: Path) -> None:
    results = load_results(write_results(tmp_path))["qa_finetuned"]
    scores = per_row_scores(results, "test", "full")
    assert scores[("t2", "registrar")] == pytest.approx(2 / 3)  # one seed of three missed it
    assert scores[("t1", "registrar")] == 1.0
    body = per_row_scores(results, "test", "body_only")
    assert {f for _, f in body} == {"fresh_issue_size"}  # the registrar has no body-only row
    assert body[("t3", "fresh_issue_size")] == 0.0  # t3 is masked to a miss in the fixture


def test_summary_has_n_interval_and_seed_spread(tmp_path: Path) -> None:
    results = load_results(write_results(tmp_path))
    ft = rung_summary(results["qa_finetuned"], "test", "full")
    assert ft["n"] == 6
    assert ft["n_ipos"] == 3
    assert ft["nvm"] == pytest.approx((5 + 2 / 3) / 6, abs=1e-4)
    low, high = ft["nvm_ci95"]
    assert low <= ft["nvm"] <= high
    assert ft["nvm_seed_std"] is not None
    assert ft["nvm_seed_std"] > 0
    assert rung_summary(results["rules"], "test", "full")["nvm_seed_std"] is None


def test_table_files_and_paired_differences(tmp_path: Path) -> None:
    table = build(load_results(write_results(tmp_path)))
    assert table["headline_split"] == "test"
    assert set(table["ladder"]) == {"rules", "qa_pretrained", "qa_finetuned"}
    gain = table["paired_test"]["qa_finetuned_minus_qa_pretrained"]["full"]
    assert gain["diff"] > 0.5  # the fixture's fine-tuned rung is far ahead of the pretrained one
    assert gain["ci95"][0] <= gain["diff"] <= gain["ci95"][1]
    assert table["per_field_test"]["rules"]["full"]["registrar"] == {"n": 3, "nvm": 1.0}

    written = write_all(table, tmp_path)
    assert [p.name for p in written] == [
        "ladder_table.json",
        "ladder_table.csv",
        "ladder_table.tex",
    ]
    rows = list(csv.DictReader(written[1].open(encoding="utf-8")))
    assert len(rows) == 3 * 2 * 2  # rungs x splits x settings
    ft = next(
        r for r in rows if (r["rung"], r["split"], r["setting"]) == ("qa_finetuned", "test", "full")
    )
    assert ft["n"] == "6"
    tex = written[2].read_text(encoding="utf-8")
    assert tex.startswith("\\begin{tabular}")
    assert "Rung 3: fine-tuned QA" in tex


def test_choice_uses_dev_only_and_ties_go_to_the_simplest_rung(tmp_path: Path) -> None:
    choice = choose_extractors(load_results(write_results(tmp_path)))
    # registrar: rules and the fine-tuned seeds are perfect on dev; the tie goes to rules
    assert choice["registrar"]["extractor"] == "rules"
    # fresh issue: the fine-tuned rung is perfect on dev, rules only half
    assert choice["fresh_issue_size"]["extractor"] == "qa_finetuned"
    assert set(choice["fresh_issue_size"]["dev"]) == {"rules", "qa_pretrained", "qa_finetuned"}
    # test rows never enter the choice: break test, the choice is unchanged
    results = load_results(tmp_path / "ladder")
    for rung_files in results.values():
        for res in rung_files:
            for row in res["predictions"]:
                if IPOS[row["ipo_id"]] == "test":
                    row["full"] = pred(False)
    assert choose_extractors(results) == choice


def test_headline_is_written_from_the_numbers_and_states_the_unmet_target(tmp_path: Path) -> None:
    table = build(load_results(write_results(tmp_path)))
    text = table["headline"]
    gain = table["paired_test"]["qa_finetuned_minus_qa_pretrained"]["full"]
    assert f"{gain['diff']:+.2f}" in text
    assert text.startswith("Fine-tuning beats the pretrained model")
    assert "rules win on templated cover pages" in text
    assert "not met" in text
    assert "ahead on 0" in text or "ahead on 1" in text or "ahead on 2" in text


def test_the_strict_metric_run_is_kept_beside_the_fixed_one(tmp_path: Path) -> None:
    results = load_results(write_results(tmp_path))
    strict_dir = tmp_path / "strict"
    strict_dir.mkdir()
    for files in copy.deepcopy(results).values():
        for res in files:
            if res["name"] == "rules":
                res["predictions"][0]["full"]["nvm"] = not res["predictions"][0]["full"]["nvm"]
            (strict_dir / f"{res['name']}.json").write_text(json.dumps(res), encoding="utf-8")
    table = build(results, load_results(strict_dir))
    assert set(table["strict_metric"]) == {"note", "ladder", "paired_test", "choice_on_dev"}
    assert "ignoring case only" in table["strict_metric"]["note"]
    assert (
        table["ladder"]["rules"]["dev"]["full"]
        != table["strict_metric"]["ladder"]["rules"]["dev"]["full"]
    )
    assert "strict_metric" not in build(results)


def test_heatmap_examples_are_at_most_five_per_cell_and_misses_come_first(tmp_path: Path) -> None:
    from finsight.evaluate.ladder import cell_examples

    results = load_results(write_results(tmp_path))["rules"]
    out = cell_examples(results, "test", "full", k=2)
    assert set(out) == {"fresh_issue_size", "registrar"}
    assert all(len(v) <= 2 for v in out.values())
    fresh = out["fresh_issue_size"]
    assert [e["correct"] for e in fresh] == sorted(e["correct"] for e in fresh)  # misses first
    assert {e["ipo_id"] for e in fresh} <= {"t1", "t2", "t3"}  # test IPOs only
    assert set(fresh[0]) == {"ipo_id", "doc", "read", "page", "checked", "correct"}
