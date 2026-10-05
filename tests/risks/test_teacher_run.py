import json
from pathlib import Path

import pytest

from finsight.risks.teacher_run import done_ids, read_jsonl, run_teacher


def items(n: int) -> list[dict[str, object]]:
    return [
        {"risk_id": f"r{i}", "messages": [{"role": "user", "content": f"risk {i}"}]}
        for i in range(n)
    ]


class Fake:
    def __init__(self) -> None:
        self.batches: list[int] = []

    def __call__(self, chats: list[list[dict[str, str]]]) -> list[str]:
        self.batches.append(len(chats))
        return [json.dumps({"echo": c[-1]["content"]}) for c in chats]


def test_batches_checkpoint_and_meta(tmp_path: Path) -> None:
    out, gen = tmp_path / "t" / "raw.jsonl", Fake()
    stats = run_teacher(items(250), gen, out, every=100, meta={"model": "m", "prompt_version": "v"})
    assert stats == {"skipped": 0, "written": 250}
    assert gen.batches == [100, 100, 50]
    rows = list(read_jsonl(out))
    assert [r["risk_id"] for r in rows] == [f"r{i}" for i in range(250)]
    assert rows[0]["model"] == "m"
    assert json.loads(rows[7]["raw"]) == {"echo": "risk 7"}


def test_rerun_resumes_and_skips_a_cut_line(tmp_path: Path) -> None:
    out = tmp_path / "raw.jsonl"
    run_teacher(items(30), Fake(), out, every=10, limit=20)
    with out.open("a", encoding="utf-8") as f:
        f.write('{"risk_id": "r20", "ra')  # the session stopped mid-write
    assert len(done_ids(out)) == 20
    gen = Fake()
    stats = run_teacher(items(30), gen, out, every=10)
    assert stats == {"skipped": 20, "written": 10}
    assert done_ids(out) == {f"r{i}" for i in range(30)}


def test_limit_counts_new_items_only(tmp_path: Path) -> None:
    out = tmp_path / "raw.jsonl"
    run_teacher(items(10), Fake(), out, every=4, limit=5)
    assert len(done_ids(out)) == 5
    assert run_teacher(items(10), Fake(), out, every=4, limit=3)["written"] == 3


def test_wrong_answer_count_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="answers"):
        run_teacher(items(3), lambda chats: ["x"], tmp_path / "raw.jsonl")
    assert not list(read_jsonl(tmp_path / "raw.jsonl"))  # nothing half-written


def test_after_batch_runs_once_per_checkpoint(tmp_path: Path) -> None:
    calls: list[int] = []
    out = tmp_path / "raw.jsonl"
    run_teacher(
        items(250), Fake(), out, every=100, after_batch=lambda: calls.append(len(done_ids(out)))
    )
    assert calls == [100, 200, 250]  # the hook sees each batch already on disk
