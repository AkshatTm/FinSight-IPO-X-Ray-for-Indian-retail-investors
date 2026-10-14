"""gpu_jobs.py: push / status / pull against a folder standing in for the HF job repo."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


gj = load("gpu_jobs", "scripts/gpu_jobs.py")
common = load("colab_common2", "notebooks/colab/_common.py")
log_compute = load("log_compute2", "scripts/log_compute.py")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A fake project root with the files push needs."""
    (tmp_path / "notebooks" / "colab").mkdir(parents=True)
    (tmp_path / "notebooks" / "colab" / "_common.py").write_text("# common\n", encoding="utf-8")
    (tmp_path / "notebooks" / "colab" / "c2_teacher.ipynb").write_text("{}", encoding="utf-8")
    inp = tmp_path / "data" / "processed" / "teacher" / "bakeoff"
    inp.mkdir(parents=True)
    (inp / "bakeoff_risks.jsonl").write_text('{"risk_id": "a"}\n{"risk_id": "b"}\n', "utf-8")
    return tmp_path


def test_push_uploads_inputs_common_and_notebooks(repo: Path, tmp_path: Path) -> None:
    store = common.DirBackend(tmp_path / "hub")
    sent = gj.push(gj.JOBS["bakeoff"], store, root=repo)
    assert "bakeoff/in/bakeoff_risks.jsonl" in sent
    assert "_common.py" in sent
    assert "notebooks/c2_teacher.ipynb" in sent
    assert (tmp_path / "hub" / "bakeoff" / "in" / "bakeoff_risks.jsonl").exists()


def test_push_fails_clearly_when_input_missing(tmp_path: Path) -> None:
    (tmp_path / "notebooks" / "colab").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="bakeoff_risks"):
        gj.push(gj.JOBS["bakeoff"], common.DirBackend(tmp_path / "hub"), root=tmp_path)


def _fake_run(hub: Path, finished: bool) -> None:
    out = hub / "bakeoff" / "out"
    out.mkdir(parents=True)
    (out / "raw_qwen3-14b-awq.jsonl").write_text('{"risk_id": "a"}\n{"risk_id": "b', "utf-8")
    (out / "run_summary_qwen3-14b-awq.json").write_text('{"written": 1}', "utf-8")
    if finished:
        summary = {
            "job": "bakeoff", "preset": "bakeoff", "finished_utc": "2026-10-16T01:00:00+00:00",
            "gpu_class": "A100", "wall_seconds": 3600, "units_before": None,
            "units_after": None, "smoke": False,
        }  # fmt: skip
        (out / "run_summary.json").write_text(json.dumps(summary), "utf-8")


def test_status_counts_rows_and_ignores_torn_line(repo: Path, tmp_path: Path) -> None:
    _fake_run(tmp_path / "hub", finished=False)
    store = common.DirBackend(tmp_path / "hub")
    info = gj.status(gj.JOBS["bakeoff"], store, root=repo)
    assert info["rows"] == {"raw_qwen3-14b-awq.jsonl": 1}
    assert info["target"] == 2
    assert info["done"] is False
    (tmp_path / "hub" / "bakeoff" / "out" / "run_summary.json").write_text(
        '{"preset": "bakeoff"}', "utf-8"
    )
    assert gj.status(gj.JOBS["bakeoff"], store, root=repo)["done"]


def test_pull_writes_expected_paths_patches_units_and_logs(repo: Path, tmp_path: Path) -> None:
    _fake_run(tmp_path / "hub", finished=True)
    log = tmp_path / "compute_log.jsonl"
    written = gj.pull(
        gj.JOBS["bakeoff"], common.DirBackend(tmp_path / "hub"), root=repo,
        units_before=190.0, units_after=182.0,
        log=lambda rows: log_compute.append_rows(rows, log),
    )  # fmt: skip
    base = "data/processed/teacher/bakeoff/"
    assert f"{base}raw_qwen3-14b-awq.jsonl" in written
    assert f"{base}run_summary_qwen3-14b-awq.json" in written
    assert "eval_results/c/bakeoff_run_summary.json" in written
    summary = json.loads((repo / "eval_results/c/bakeoff_run_summary.json").read_text())
    assert summary["units_used"] == 8.0
    assert summary["units_per_hour_observed"] == 8.0
    rows = log_compute.read_log(log)
    assert len(rows) == 1
    assert rows[0]["units_used"] == 8.0


def test_teacher_full_single_raw_becomes_raw_jsonl(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "hub" / "teacher_full" / "out"
    out.mkdir(parents=True)
    (out / "raw_qwen3-32b-awq.jsonl").write_text('{"risk_id": "a"}\n', "utf-8")
    written = gj.pull(gj.JOBS["teacher_full"], common.DirBackend(tmp_path / "hub"), root=repo)
    assert "data/processed/teacher/raw.jsonl" in written
    assert (repo / "data/processed/teacher/raw.jsonl").read_text() == '{"risk_id": "a"}\n'


def test_pull_with_nothing_yet_is_an_error(repo: Path, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="nothing under"):
        gj.pull(gj.JOBS["bakeoff"], common.DirBackend(tmp_path / "hub"), root=repo)


def test_patch_units_keeps_missing_values() -> None:
    s = gj.patch_units({"wall_seconds": 1800}, 100.0, None)
    assert s["units_before"] == 100.0
    assert "units_used" not in s
