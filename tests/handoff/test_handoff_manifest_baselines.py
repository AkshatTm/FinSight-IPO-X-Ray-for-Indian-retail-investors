"""Manifest placement (git vs HF) and the baselines assembly."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finsight.handoff import build_baselines, build_manifest, manifest


def test_files_over_the_limit_go_to_hf_and_are_gitignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manifest, "GIT_LIMIT_BYTES", 10)
    (tmp_path / "small.txt").write_text("hi", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "big.bin").write_bytes(b"x" * 50)
    m = build_manifest(tmp_path, "o/r", "p/data", "abc")
    rows = {f["path"]: f for f in m["files"]}
    assert rows["small.txt"]["where"] == "git"
    assert rows["sub/big.bin"]["where"] == "hf"
    assert rows["sub/big.bin"]["hf"] == {
        "repo": "o/r",
        "type": "dataset",
        "path": "p/data/sub/big.bin",
        "revision": "abc",
    }
    assert len(rows["small.txt"]["sha256"]) == 64
    assert "/sub/big.bin" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_baselines_copy_numbers_from_the_sources() -> None:
    classifier = {
        "category": {
            "seeds": [13, 42, 2026],
            "n_dev": 1060,
            "dev_macro_f1_mean": 0.8923,
            "dev_macro_f1_sd": 0.0062,
            "test_macro_f1_mean": 0.8986,
            "test_label_source": "human:akshat",
        },
        "seriousness": {
            "seeds": [13, 42, 2026],
            "dev_by_seed": {"13": {}},
            "dev_mean": {
                "macro_f1": 0.76,
                "mae": 0.19,
                "severe_recall": 0.5575,
                "severe_precision": 0.56,
            },
        },
    }
    cell = {"mean": 0.333, "low": 0.1, "high": 0.5}
    bench = {
        "systems": {
            "student": {
                "A": {"nvm": {"mean": 0.34}},
                "B": {},
                "C": {
                    "hallucinated_number_unanswerable": cell,
                    "abstention_unanswerable": cell,
                    "correct_answerable": {"mean": 0.49},
                    "verified_share": {"mean": 0.6},
                },
            },
            "rules_v1": {"A": {"nvm": {"mean": 0.72}}},
        }
    }
    rating = {
        "systems": {
            "student": {
                "faithful_yes_share": 0.92,
                "faithful_yes_ci95": [0.8, 0.9],
                "plain_english_mean": 4.64,
            }
        }
    }
    checks = {"n": 50, "systems": {"student": {"passed": 49, "mean_words": 43.2}}}
    ev = {"e19_readability": {"gold50": {"fkgl_drop": 8.47}}}
    out = build_baselines(
        classifier,
        {"dev": {"severe_support": 58}},
        bench,
        rating,
        checks,
        ev,
        {"x": {"path": "p", "sha256": "0"}},
    )
    assert out["m4_severity"]["severe_recall_mean"] == 0.5575
    assert out["m4_severity"]["severe_support_dev"] == 58
    assert out["guardrail_category"]["dev_macro_f1_mean"] == 0.8923
    assert out["m1_chat_bench_v1"]["hallucinated_number_on_unanswerable"]["mean"] == 0.333
    assert out["m1_rewrite_gold50"]["post_check_pass"] == 49
    json.dumps(out)  # serialisable
