import json
from pathlib import Path

import pytest

from finsight.weaklabel.package import package_dataset


def write_rows(path: Path, n: int, prefix: str) -> None:
    rows = [
        {
            "id": f"{prefix}{i}", "ipo_id": f"{prefix}-ipo{i % 5}", "field_id": "registrar",
            "title": "t", "question": "q?", "context": "ctx",
            "answers": (
                {"text": ["ctx"], "answer_start": [0]}
                if i % 2 == 0
                else {"text": [], "answer_start": []}
            ),
        }
        for i in range(n)
    ]  # fmt: skip
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


@pytest.fixture
def source(tmp_path: Path) -> Path:
    src = tmp_path / "weaklabel"
    src.mkdir()
    write_rows(src / "train.jsonl", 500, "tr")
    write_rows(src / "dev.jsonl", 60, "dv")
    return src


def test_package_writes_files_metadata_and_slice(source: Path, tmp_path: Path) -> None:
    out = package_dataset(source, tmp_path / "pkg", "akshat-user", slice_size=200)
    names = {p.name for p in out.iterdir()}
    assert names == {"train.jsonl", "dev.jsonl", "train_200.jsonl", "dev_200.jsonl",
                     "dataset-metadata.json", "README.md"}  # fmt: skip
    meta = json.loads((out / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert meta["id"] == "akshat-user/finsight-weaklabel"
    assert meta["title"] == "finsight-weaklabel"
    assert meta["licenses"] == [{"name": "CC-BY-NC-SA-4.0"}]
    assert sum(1 for _ in (out / "train_200.jsonl").open(encoding="utf-8")) == 200
    assert sum(1 for _ in (out / "dev_200.jsonl").open(encoding="utf-8")) == 60  # fewer than 200
    assert (out / "train.jsonl").read_bytes() == (source / "train.jsonl").read_bytes()


def test_slice_keeps_positives_and_negatives_and_is_repeatable(
    source: Path, tmp_path: Path
) -> None:
    out = package_dataset(source, tmp_path / "a", "user-one", slice_size=100)
    rows = [
        json.loads(x) for x in (out / "train_200.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 100
    positives = sum(bool(r["answers"]["text"]) for r in rows)
    assert 30 <= positives <= 70
    again = package_dataset(source, tmp_path / "b", "user-one", slice_size=100)
    assert (again / "train_200.jsonl").read_text() == (out / "train_200.jsonl").read_text()


def test_package_refuses_missing_inputs_and_a_bad_username(source: Path, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="weaklabel build"):
        package_dataset(tmp_path / "nope", tmp_path / "pkg", "user-one")
    with pytest.raises(ValueError, match="username"):
        package_dataset(source, tmp_path / "pkg", "Not A User!")
