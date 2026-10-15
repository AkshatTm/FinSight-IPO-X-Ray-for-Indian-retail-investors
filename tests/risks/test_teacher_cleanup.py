"""C2.3b: strict number checks, category remap, non-risk titles, bands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import finsight.risks.teacher_cleanup as tc
from finsight.risks.strict_numbers import strict_check
from finsight.risks.teacher_cleanup import (
    clean,
    is_nonrisk_title,
    load_rules,
    remap_category,
    seriousness_band,
)


def reasons(original: str, simple: str) -> list[str]:
    return [f.reason for f in strict_check(original, simple)]


def test_unit_dropped_scale_and_currency() -> None:
    src = "Our borrowings were ₹285.97 million as of March 31, 2024."
    assert reasons(src, "Borrowings were 285.97 in March 2024.") == ["unit_dropped"]
    assert reasons(src, "Borrowings were ₹285.97 million in March 2024.") == []


def test_small_counts_are_not_units() -> None:
    assert reasons("We have ₹5 million and 3 plants.", "It has 3 plants.") == []


def test_sign_flip_only_bracketed_is_negative() -> None:
    src = "Net cash flow was 285.97, (60.17) and 297.14 in Fiscals 2024, 2023 and 2022."
    out = strict_check(src, "Cash flow was negative: 285.97, (60.17) and 297.14.")
    assert {f.detail.split()[0] for f in out if f.reason == "sign_flip"} == {"285.97", "297.14"}


def test_negative_word_in_source_is_accepted() -> None:
    src = "We had negative cash flows of ₹447.73 million, ₹879.96 million and ₹1,210.15 million."
    assert reasons(src, "It had negative cash flows of ₹447.73 million, ₹879.96 million.") == []


def test_years_are_not_figures() -> None:
    src = "We had a loss in 2023."
    assert reasons(src, "It had negative results in 2023.") == []


def test_inclusion_polarity_is_a_flag_not_a_drop() -> None:
    src = "The total of 109.56 does not include 7.32 of tax in excess of provisions."
    found = strict_check(src, "The 7.32 tax excess is included in the 109.56 total.")
    assert [f.reason for f in found] == ["inclusion_polarity"]
    assert not found[0].drops


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("We depend on our key personnel and senior management.", "operations"),
        ("Rights of shareholders under Indian law may differ", "regulatory"),
        ("The objects of the Issue have not been appraised", "financial"),
        ("Our joint venture partner may deadlock decisions", "operations"),
        ("Negative publicity could damage our brand", "operations"),
        ("The auditors' report contains CARO remarks on statutory dues", "financial"),
    ],
)
def test_remap_rules(title: str, expected: str) -> None:
    new, rule = remap_category(title, "", "promoters_governance", load_rules())
    assert (new, rule is not None) == (expected, True)


def test_remap_leaves_unmatched() -> None:
    assert remap_category("Our plant may shut", "", "operations", load_rules()) == (
        "operations",
        None,
    )


def test_nonrisk_titles() -> None:
    assert is_nonrisk_title("Currency of Presentation – Financial Data of Subsidiaries")
    assert is_nonrisk_title("Nine Months Ended December 31, 2023")
    assert not is_nonrisk_title("We may not be able to repay our borrowings on time.")
    assert not is_nonrisk_title("")


def test_band_merges_4_and_5() -> None:
    assert [seriousness_band(n) for n in (1, 2, 3, 4, 5)] == [1, 2, 3, 4, 4]


def test_clean_writes_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tc, "REPORT_PATH", tmp_path / "report.json")
    risks = [
        {"risk_id": "a#r1", "title": "We depend on key personnel"},
        {"risk_id": "a#r2", "title": "Net cash flows"},
    ]
    pairs = [
        {
            "risk_id": "a#r1",
            "company": "A",
            "original": "Title: We depend on key personnel\n\nbody",
            "simple": "It depends on people.",
            "label_source": "t",
        },
        {
            "risk_id": "a#r2",
            "company": "A",
            "original": "Title: Net cash flows\n\nCash flow was 285.97, (60.17).",
            "simple": "Cash flow was negative: 285.97 and (60.17).",
            "label_source": "t",
        },
    ]
    labels = [
        {
            "risk_id": "a#r1",
            "company": "A",
            "category": "promoters_governance",
            "seriousness_1to5": 5,
            "hard_fact": False,
            "label_source": "t",
        },
        {
            "risk_id": "a#r2",
            "company": "A",
            "category": "financial",
            "seriousness_1to5": 2,
            "hard_fact": True,
            "label_source": "t",
        },
    ]
    for name, rows in (("risks", risks), ("simplify", pairs), ("labels", labels)):
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
        )
    report = clean(tmp_path)
    assert report["pairs_kept"] == 1
    assert report["strict_dropped"] == {"sign_flip": 1}
    out = [json.loads(x) for x in (tmp_path / "labels.clean.jsonl").read_text().splitlines()]
    assert out[0]["category"] == "operations"
    assert out[0]["category_teacher"] == "promoters_governance"
    assert out[0]["seriousness_band"] == 4
    assert len(out) == 2  # labels keep the dropped-rewrite row
