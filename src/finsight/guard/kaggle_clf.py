"""Run the MuRIL advice-classifier notebook on Kaggle from the laptop (P5.4; nothing trains here).

    uv run python -m finsight.guard.clf_data --username <u>            # split + package
    (cd data/processed/kaggle/finsight-advice && kaggle datasets create -p .)   # first time
    uv run python -m finsight.guard.kaggle_clf push smoke|full --username <u>
    uv run python -m finsight.guard.kaggle_clf status smoke|full --username <u>
    uv run python -m finsight.guard.kaggle_clf fetch smoke|full --username <u>

``fetch full`` keeps the weights of the seed with the best **validation** F1 in
``models/guard_clf/`` (never committed) and writes ``eval_results/guard_clf.json`` with the
three seeds' validation and test scores as the notebook wrote them. Nothing is edited.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.guard.clf_data import DATASET_NAME
from finsight.weaklabel.kaggle import ACCELERATOR, CODE_FILE, _kaggle, render_notebook

NOTEBOOK = Path(__file__).resolve().parents[3] / "notebooks" / "03_muril_guard.ipynb"
SEEDS = (13, 42, 2026)


def run_params(run: str) -> dict[str, Any]:
    if run == "smoke":
        return {"SEEDS": [SEEDS[0]], "EPOCHS": 1}
    if run == "full":
        return {"SEEDS": list(SEEDS)}
    raise ValueError(f"run must be 'smoke' or 'full'; got {run!r}")


def kernel_slug(run: str) -> str:
    run_params(run)
    return f"finsight-muril-guard-{run}"


def write_kernel(folder: Path, username: str, run: str, notebook: Path = NOTEBOOK) -> Path:
    nb = render_notebook(json.loads(notebook.read_text(encoding="utf-8")), run_params(run))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / CODE_FILE).write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8", newline="\n")
    slug = kernel_slug(run)
    meta = {
        "id": f"{username}/{slug}",
        "title": slug,
        "code_file": CODE_FILE,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",  # the base model comes from the Hugging Face Hub
        "dataset_sources": [f"{username}/{DATASET_NAME}"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (folder / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    return folder


def check_metrics(metrics: dict[str, Any], weight_files: list[str]) -> list[str]:
    problems = []
    for part in ("val", "test"):
        f1 = (metrics.get(part) or {}).get("f1")
        if not (isinstance(f1, int | float) and math.isfinite(f1)):
            problems.append(f"{part} F1 is missing or not a number")
    if not any(n.startswith("model.") for n in weight_files):
        problems.append("no model weights in final/")
    return problems


def collect(downloaded: Path, run: str, models_dir: Path, eval_dir: Path) -> dict[str, Any]:
    seeds = run_params(run)["SEEDS"]
    per_seed, problems = {}, []
    for seed in seeds:
        mfile = next(iter(sorted(downloaded.rglob(f"metrics-{seed}.json"))), None)
        if mfile is None:
            problems.append(f"seed {seed}: no metrics file")
            continue
        metrics = json.loads(mfile.read_text(encoding="utf-8"))
        finals = [p for p in downloaded.rglob("final") if p.parent.name == f"seed-{seed}"]
        files = [p.name for p in finals[0].iterdir()] if finals else []
        problems += [f"seed {seed}: {p}" for p in check_metrics(metrics, files)]
        per_seed[seed] = {"metrics": metrics, "final": finals[0] if finals else None}
    report = {"run": run, "problems": problems, "seeds": {}}
    if run == "smoke" or problems:
        return report
    best = max(per_seed, key=lambda s: per_seed[s]["metrics"]["val"]["f1"])
    report["best_seed_by_val_f1"] = best
    report["seeds"] = {str(s): v["metrics"] for s, v in per_seed.items()}
    target = models_dir / "guard_clf"
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(per_seed[best]["final"]), str(target))
    eval_dir.mkdir(parents=True, exist_ok=True)
    out = {"experiment": "E8-classifier", "model": "google/muril-base-cased", **report}
    (eval_dir / "guard_clf.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="finsight.guard.kaggle_clf")
    parser.add_argument("command", choices=("push", "status", "fetch"))
    parser.add_argument("run", choices=("smoke", "full"))
    parser.add_argument("--username", default=os.environ.get("KAGGLE_USERNAME", ""))
    args = parser.parse_args(argv)
    if not args.username:
        parser.error("pass --username or set KAGGLE_USERNAME")
    username, slug = args.username.lower(), kernel_slug(args.run)
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
    report = collect(out, args.run, paths.models_dir, paths.eval_dir)
    for seed, m in report["seeds"].items():
        t = m["test"]
        print(f"seed {seed}: val F1 {m['val']['f1']:.3f}  test F1 {t['f1']:.3f}  "
              f"block {t['block_rate']:.3f}  false block {t['false_block_rate']:.3f}")  # fmt: skip
    for problem in report["problems"]:
        print("PROBLEM:", problem)
    print("FAILED" if report["problems"] else f"OK: {args.run}")
    if args.run == "smoke":
        shutil.rmtree(out)
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
