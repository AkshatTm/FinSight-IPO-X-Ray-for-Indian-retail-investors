"""Run the fine-tuning notebook on Kaggle from the laptop (nothing trains locally; ADR-042).

    uv run python -m finsight.weaklabel.kaggle push smoke     # 200-example slice, seed 13, 1 epoch
    uv run python -m finsight.weaklabel.kaggle push 13        # one full run per seed: 13, 42, 2026
    uv run python -m finsight.weaklabel.kaggle status 13
    uv run python -m finsight.weaklabel.kaggle fetch 13       # weights and metrics come home

A run is one private Kaggle notebook: a copy of ``notebooks/01_finetune_extractor.ipynb`` with
its parameters cell rewritten, plus ``kernel-metadata.json`` (GPU and Internet on, the private
``finsight-weaklabel`` dataset attached). The official ``kaggle`` CLI does the talking and reads
its own token; this module never opens, prints or logs it.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.weaklabel.package import DATASET_NAME, SLICE_SIZE

NOTEBOOK = Path(__file__).resolve().parents[3] / "notebooks" / "01_finetune_extractor.ipynb"
SEEDS = (13, 42, 2026)
ACCELERATOR = "NvidiaTeslaT4"  # the P100 is too old for current PyTorch builds
CODE_FILE = "notebook.ipynb"
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9-]{2,}$")


def run_params(run: str) -> dict[str, Any]:
    """``smoke`` or a seed number -> the values written into the parameters cell."""
    if run == "smoke":
        return {"SLICE": SLICE_SIZE, "SEEDS": [SEEDS[0]], "EPOCHS": 1}
    if run.isdigit() and int(run) in SEEDS:
        return {"SLICE": None, "SEEDS": [int(run)], "EPOCHS": 3}
    raise ValueError(f"run must be 'smoke' or one of {', '.join(map(str, SEEDS))}; got {run!r}")


def kernel_slug(run: str) -> str:
    run_params(run)
    return "finsight-extractor-smoke" if run == "smoke" else f"finsight-extractor-seed-{run}"


def render_notebook(nb: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """A copy of the notebook with ``NAME = value`` lines of the parameters cell replaced."""
    out: dict[str, Any] = json.loads(json.dumps(nb))
    cells = [c for c in out["cells"] if "parameters" in c.get("metadata", {}).get("tags", [])]
    if len(cells) != 1:
        raise ValueError("the notebook needs exactly one cell tagged 'parameters'")
    lines = "".join(cells[0]["source"]).splitlines(keepends=True)
    for name, value in params.items():
        hits = [i for i, line in enumerate(lines) if re.match(rf"{name}\s*=", line)]
        if len(hits) != 1:
            raise ValueError(f"parameter {name} must be assigned exactly once in the cell")
        lines[hits[0]] = f"{name} = {value!r}\n"
    cells[0]["source"] = lines
    return out


def kernel_metadata(username: str, run: str) -> dict[str, Any]:
    if not _USERNAME.match(username):
        raise ValueError(f"username {username!r} is not a Kaggle username (lowercase, digits, -)")
    slug = kernel_slug(run)
    return {
        "id": f"{username}/{slug}",
        "title": slug,  # Kaggle derives the slug from the title: keep them equal
        "code_file": CODE_FILE,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",  # the base model is downloaded from the Hugging Face Hub
        "dataset_sources": [f"{username}/{DATASET_NAME}"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }


def write_kernel(folder: Path, username: str, run: str, notebook: Path = NOTEBOOK) -> Path:
    """The folder ``kaggle kernels push -p`` uploads: the rendered notebook and its metadata."""
    nb = render_notebook(json.loads(notebook.read_text(encoding="utf-8")), run_params(run))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / CODE_FILE).write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8", newline="\n")
    meta = kernel_metadata(username, run)
    (folder / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    return folder


def check_run(metrics: dict[str, Any], weight_files: list[str]) -> list[str]:
    """Problems with a finished run; an empty list means it passed (loss fell, files exist)."""
    problems = []
    losses = [float(x) for x in metrics.get("loss_history") or []]
    if len(losses) < 2:
        problems.append("fewer than two logged losses: cannot tell whether the loss went down")
    elif not all(math.isfinite(x) for x in losses):
        problems.append("loss history has NaN or infinity")
    elif not losses[-1] < losses[0]:
        problems.append(f"loss did not go down ({losses[0]:.3f} -> {losses[-1]:.3f})")
    f1 = metrics.get("F1")
    if f1 is None or not math.isfinite(float(f1)):
        problems.append("F1 is missing or not a number")
    if not any(name.startswith("model.") for name in weight_files):
        problems.append("no model weights (model.safetensors) in final/")
    if "config.json" not in weight_files:
        problems.append("no config.json in final/")
    return problems


def collect(downloaded: Path, run: str, models_dir: Path, eval_dir: Path) -> dict[str, Any]:
    """Move a run's weights to ``models/extractor/`` and its metrics to ``eval_results/``.

    The smoke run is only checked: its weights and metrics are not kept as results.
    """
    seed = run_params(run)["SEEDS"][0]
    metrics_file = next(iter(sorted(downloaded.rglob(f"metrics-{seed}.json"))), None)
    finals = [p for p in sorted(downloaded.rglob("final")) if p.parent.name == f"seed-{seed}"]
    final = next((p for p in finals if p.is_dir()), None)
    if metrics_file is None or final is None:
        raise FileNotFoundError(f"{downloaded} has no metrics-{seed}.json and seed-{seed}/final/")
    metrics: dict[str, Any] = json.loads(metrics_file.read_text(encoding="utf-8"))
    problems = check_run(metrics, [p.name for p in final.iterdir()])
    result = {"run": run, "seed": seed, "problems": problems, "metrics": metrics}
    if run == "smoke" or problems:
        return result
    target = models_dir / "extractor" / f"seed-{seed}"
    target.mkdir(parents=True, exist_ok=True)
    for p in final.iterdir():
        shutil.copy2(p, target / p.name)
    eval_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(metrics_file, eval_dir / f"extractor_metrics-{seed}.json")  # never edited
    return result


def _kaggle(*args: str) -> int:
    exe = shutil.which("uvx")
    if exe is None:
        raise FileNotFoundError("uvx is not on PATH (install uv)")
    return subprocess.run([exe, "kaggle", *args], check=False).returncode


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.weaklabel.kaggle")
    parser.add_argument("command", choices=("push", "status", "fetch"))
    parser.add_argument("run", help="smoke | 13 | 42 | 2026")
    parser.add_argument("--username", default=os.environ.get("KAGGLE_USERNAME", ""))
    args = parser.parse_args(argv)
    if not args.username:
        parser.error("pass --username or set KAGGLE_USERNAME")
    username = args.username.lower()
    slug = kernel_slug(args.run)
    paths = get_settings().paths
    work = paths.processed_dir / "kaggle"
    if args.command == "push":
        folder = write_kernel(work / "kernels" / slug, username, args.run)
        return _kaggle("kernels", "push", "-p", str(folder), "--accelerator", ACCELERATOR)
    if args.command == "status":
        return _kaggle("kernels", "status", f"{username}/{slug}")
    out = work / "output" / slug
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    code = _kaggle("kernels", "output", f"{username}/{slug}", "-p", str(out), "-o", "-q")
    if code != 0:
        return code
    result = collect(out, args.run, paths.models_dir, paths.eval_dir)
    keep = ("EM", "F1", "HasAns_F1", "NoAns_acc", "n_train", "train_runtime_s", "final_train_loss")
    print(json.dumps({k: result["metrics"].get(k) for k in keep}))
    for problem in result["problems"]:
        print("PROBLEM:", problem)
    print("FAILED" if result["problems"] else f"OK: {args.run}")
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
