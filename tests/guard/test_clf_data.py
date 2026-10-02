import csv
from pathlib import Path

import pytest

from finsight.guard.clf_data import load_questions, split_questions, write_dataset
from finsight.guard.kaggle_clf import kernel_slug, run_params, write_kernel

HEADER = "question,language,is_advice (must block?),tricky_note,reviewed_by_akshat (Y/edit)\n"


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    lines = [HEADER]
    for lang in ("en", "hi"):
        for i in range(20):
            lines.append(f"Should I buy {lang} {i}?,{lang},yes,,\n")
            lines.append(f"What is the price {lang} {i}?,{lang},no,,\n")
    lines.append("Should I buy en 0?,en,yes,,\n")  # a repeat
    path = tmp_path / "set.csv"
    path.write_text("".join(lines), encoding="utf-8-sig")
    return path


def test_split_is_disjoint_stratified_and_repeatable(csv_path: Path) -> None:
    rows = load_questions(csv_path)
    assert len(rows) == 80  # the repeat is dropped
    a, b = split_questions(rows), split_questions(rows)
    assert a == b
    names = [{r["question"] for r in a[p]} for p in ("train", "val", "test")]
    assert not names[0] & names[1]
    assert not names[0] & names[2]
    assert not names[1] & names[2]
    assert sum(len(n) for n in names) == 80
    for part in a.values():
        assert {(r["language"], r["label"]) for r in part} == {
            ("en", "advice"), ("en", "fact"), ("hi", "advice"), ("hi", "fact"),
        }  # fmt: skip


def test_write_dataset_files(csv_path: Path, tmp_path: Path) -> None:
    counts = write_dataset(csv_path, tmp_path / "out", "akshat-user")
    assert sum(counts.values()) == 80
    with (tmp_path / "out" / "train.csv").open(encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["question", "language", "label"]


def test_kernel_for_each_run(tmp_path: Path) -> None:
    assert run_params("smoke") == {"SEEDS": [13], "EPOCHS": 1}
    assert kernel_slug("full") == "finsight-muril-guard-full"
    folder = write_kernel(tmp_path / "k", "akshat-user", "full")
    text = (folder / "notebook.ipynb").read_text(encoding="utf-8")
    assert "SEEDS = [13, 42, 2026]" in text
    with pytest.raises(ValueError, match="smoke"):
        run_params("other")
