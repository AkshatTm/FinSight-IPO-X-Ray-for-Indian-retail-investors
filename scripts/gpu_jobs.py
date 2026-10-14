"""Move Colab job files between the laptop and the private HF job repo (C0.2 onward).

    uv run python scripts/gpu_jobs.py push bakeoff          # inputs, _common.py and notebooks up
    uv run python scripts/gpu_jobs.py status bakeoff        # progress from the latest checkpoint
    uv run python scripts/gpu_jobs.py pull bakeoff [--units-before 190 --units-after 181.4]

The repo (``AkshatTm/finsight-gpu-jobs``, a private dataset) holds ``<job>/in/<file>`` (inputs) and
``<job>/out/<file>`` (checkpoints and results, uploaded by the notebook after every batch). A
notebook run resumes from ``out/``. ``pull`` writes the outputs to the paths the
``docs/phase3/COLAB_STEPS_*.md`` files expect and logs the run with ``scripts/log_compute.py``.
``HF_TOKEN`` comes from the environment or ``.env`` and is never printed. Tests use a
``DirBackend`` (a folder) instead of the Hub.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "AkshatTm/finsight-gpu-jobs"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


def common() -> Any:
    """``notebooks/colab/_common.py`` (the same file the notebooks use: DirBackend / HubBackend)."""
    return _load("colab_common", ROOT / "notebooks" / "colab" / "_common.py")


@dataclass
class Job:
    """One Colab job: inputs to push, and where each output is pulled to.

    ``outputs`` maps a glob (relative to ``<job>/out/``) to a local destination: a directory
    (ends with ``/``) or a file. ``summary`` is the final ``run_summary.json`` destination.
    """

    name: str
    notebook: str
    inputs: dict[str, str] = field(default_factory=dict)  # local path -> name under <job>/in/
    outputs: dict[str, str] = field(default_factory=dict)
    summary: str = "eval_results/c/{preset}_run_summary.json"
    target_from: str | None = None  # input name whose line count is the number of items to do
    single_raw_copy: str | None = None  # if exactly one raw_*.jsonl came back, also copy it here


JOBS: dict[str, Job] = {
    "rate_check": Job(
        name="rate_check",
        notebook="c0_rate_check.ipynb",
        summary="eval_results/c/{preset}_run_summary.json",
    ),
    "bakeoff": Job(
        name="bakeoff",
        notebook="c2_teacher.ipynb",
        inputs={"data/processed/teacher/bakeoff/bakeoff_risks.jsonl": "bakeoff_risks.jsonl"},
        outputs={
            "raw_*.jsonl": "data/processed/teacher/bakeoff/",
            "run_summary_*.json": "data/processed/teacher/bakeoff/",
        },
        summary="eval_results/c/bakeoff_run_summary.json",
        target_from="bakeoff_risks.jsonl",
    ),
    "teacher_full": Job(
        name="teacher_full",
        notebook="c2_teacher.ipynb",
        inputs={"data/processed/teacher/risks.jsonl": "risks.jsonl"},
        outputs={
            "raw_*.jsonl": "data/processed/teacher/raw/",
            "run_summary_*.json": "eval_results/c/",
        },
        summary="eval_results/c/teacher_full_run_summary.json",
        target_from="risks.jsonl",
        single_raw_copy="data/processed/teacher/raw.jsonl",
    ),
    "student": Job(
        name="student",
        notebook="c2_student.ipynb",
        inputs={
            "data/processed/kaggle/simplify/train.jsonl": "train.jsonl",
            "data/processed/kaggle/simplify/dev.jsonl": "dev.jsonl",
        },
        outputs={
            "adapter/*": "models/student/adapter/",
            "*.gguf": "models/student/",
            "metrics.json": "models/student/",
        },
        summary="eval_results/c/student_run_summary.json",
    ),
}


def push(job: Job, store: Any, root: Path = ROOT) -> list[str]:
    """Upload ``_common.py``, the notebooks and the job's inputs; returns the remote paths."""
    pairs: list[tuple[Path, str]] = [(root / "notebooks" / "colab" / "_common.py", "_common.py")]
    for nb in sorted((root / "notebooks" / "colab").glob("*.ipynb")):
        pairs.append((nb, f"notebooks/{nb.name}"))
    for local, name in job.inputs.items():
        src = root / local
        if not src.is_file():
            raise FileNotFoundError(f"{local} missing (build it first; see COLAB_STEPS_{job.name})")
        pairs.append((src, f"{job.name}/in/{name}"))
    store.put(pairs)
    return [r for _, r in pairs]


def _count_rows(path: Path) -> int:
    n = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                continue  # a torn last line
            n += 1
    return n


def status(job: Job, store: Any, root: Path = ROOT) -> dict[str, Any]:
    """Progress of ``<job>`` from the latest checkpoint in the repo (downloads the raw files)."""
    prefix = f"{job.name}/out/"
    files = store.ls(prefix)
    info: dict[str, Any] = {"job": job.name, "files": [f[len(prefix) :] for f in files], "rows": {}}
    if job.target_from:
        local = next((root / p for p, n in job.inputs.items() if n == job.target_from), None)
        if local is not None and local.is_file():
            info["target"] = _count_rows(local)
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            name = f[len(prefix) :]
            if fnmatch.fnmatch(name, "raw_*.jsonl"):
                dst = Path(tmp) / name
                if store.get(f, dst):
                    info["rows"][name] = _count_rows(dst)
            elif name == "run_summary.json":
                dst = Path(tmp) / name
                if store.get(f, dst):
                    s = json.loads(dst.read_text(encoding="utf-8"))
                    info["summary"] = {
                        k: s.get(k)
                        for k in ("preset", "gpu", "wall_seconds", "units_used", "smoke")
                    }
    info["done"] = "summary" in info
    return info


def patch_units(
    summary: dict[str, Any], before: float | None, after: float | None
) -> dict[str, Any]:
    """Fill ``units_before`` / ``units_after`` (typed by Akshat) and recompute the derived fields."""
    if before is not None:
        summary["units_before"] = before
    if after is not None:
        summary["units_after"] = after
    b, a, wall = (
        summary.get("units_before"),
        summary.get("units_after"),
        summary.get("wall_seconds"),
    )
    if b is not None and a is not None:
        summary["units_used"] = round(b - a, 2)
        if wall:
            summary["units_per_hour_observed"] = round((b - a) / (wall / 3600), 2)
    return summary


def pull(
    job: Job,
    store: Any,
    root: Path = ROOT,
    units_before: float | None = None,
    units_after: float | None = None,
    log: Callable[[list[dict[str, Any]]], int] | None = None,
) -> list[str]:
    """Download the job's outputs to their expected paths, patch units, log the compute row.

    Returns the local paths written (relative to ``root``).
    """
    prefix = f"{job.name}/out/"
    remote = {f[len(prefix) :]: f for f in store.ls(prefix)}
    if not remote:
        raise FileNotFoundError(f"nothing under {prefix} yet (status {job.name})")
    written: list[str] = []
    raws: list[Path] = []
    for name, rpath in sorted(remote.items()):
        if name == "run_summary.json":
            continue  # handled below
        for pattern, dest in job.outputs.items():
            if not fnmatch.fnmatch(name, pattern):
                continue
            base = Path(name).name
            local = root / dest / base if dest.endswith("/") else root / dest
            if store.get(rpath, local):
                written.append(local.relative_to(root).as_posix())
                if fnmatch.fnmatch(base, "raw_*.jsonl"):
                    raws.append(local)
            break
    if job.single_raw_copy and len(raws) == 1:
        dst = root / job.single_raw_copy
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raws[0].read_bytes())
        written.append(job.single_raw_copy)
    if "run_summary.json" in remote:
        tmp = root / "eval_results" / "c" / ".run_summary.pulled.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        store.get(remote["run_summary.json"], tmp)
        summary = patch_units(
            json.loads(tmp.read_text(encoding="utf-8")), units_before, units_after
        )
        tmp.unlink()
        dest = job.summary.format(preset=summary.get("preset") or job.name)
        out = root / dest
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
        written.append(dest)
        if log is not None:
            log([summary])
    return written


def _token() -> str | None:
    hf_upload = _load("hf_upload", ROOT / "scripts" / "hf_upload.py")
    return hf_upload.load_token()


def make_store(repo: str, create: bool) -> Any:
    """The private dataset repo as a store (created, private, on the first push)."""
    from huggingface_hub import HfApi

    tok = _token()
    if not tok:
        raise SystemExit("HF_TOKEN not set (env or .env)")
    if create:
        HfApi(token=tok).create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    return common().HubBackend(repo, tok)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["push", "status", "pull"])
    ap.add_argument("job", choices=sorted(JOBS))
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--units-before", type=float)
    ap.add_argument("--units-after", type=float)
    ap.add_argument("--no-log", action="store_true", help="pull without writing the compute log")
    a = ap.parse_args(argv)
    job = JOBS[a.job]
    store = make_store(a.repo, create=a.command == "push")
    if a.command == "push":
        sent = push(job, store)
        print(f"pushed {len(sent)} file(s) to {a.repo} (private):")
        for r in sent:
            print("  ", r)
    elif a.command == "status":
        print(json.dumps(status(job, store), indent=1))
    else:
        log = None
        if not a.no_log:
            lc = _load("log_compute", ROOT / "scripts" / "log_compute.py")
            log = lc.append_rows
        for p in pull(job, store, units_before=a.units_before, units_after=a.units_after, log=log):
            print("pulled", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
