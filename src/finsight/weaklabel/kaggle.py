"""Run the fine-tuning notebook on Kaggle from the laptop (nothing trains locally; ADR-042/043).

    uv run python -m finsight.weaklabel.kaggle push smoke     # 200-example slice, seed 13, 1 epoch
    uv run python -m finsight.weaklabel.kaggle push baseline  # no training: the model as downloaded
    uv run python -m finsight.weaklabel.kaggle push 13        # one full run per seed: 13, 42, 2026
    uv run python -m finsight.weaklabel.kaggle status 13
    uv run python -m finsight.weaklabel.kaggle fetch 13       # weights and metrics come home

A run is one private Kaggle notebook: a copy of ``notebooks/01_finetune_extractor.ipynb`` with
its parameters cell rewritten, plus ``kernel-metadata.json`` (GPU and Internet on, the private
``finsight-weaklabel`` dataset attached). The official ``kaggle`` CLI does the talking and reads
its own token; this module never opens, prints or logs it.

What counts as passing:
- smoke: it ran end to end and wrote metrics and weights. Nothing about quality.
- a seed: its best epoch beats the zero-shot baseline on dev EM and token F1 (same dev split).
  A smoothed loss that rises over the last epoch is flagged as a warning.
NVM is computed here, from the dev predictions the notebook saved, with the FinSight normalizer.
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
from finsight.evaluate import exact_match, nvm
from finsight.extract import RawAnswer, answer_value, get_field
from finsight.weaklabel.package import DATASET_NAME, SLICE_SIZE

NOTEBOOK = Path(__file__).resolve().parents[3] / "notebooks" / "01_finetune_extractor.ipynb"
SEEDS = (13, 42, 2026)
ACCELERATOR = "NvidiaTeslaT4"  # the P100 is too old for current PyTorch builds
CODE_FILE = "notebook.ipynb"
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9-]{2,}$")


def run_params(run: str) -> dict[str, Any]:
    """``smoke``, ``baseline`` or a seed number -> the values written into the parameters cell."""
    if run == "smoke":
        return {"SLICE": SLICE_SIZE, "SEEDS": [SEEDS[0]], "EPOCHS": 1}
    if run == "baseline":
        return {"SLICE": None, "ZERO_SHOT": True}
    if run.isdigit() and int(run) in SEEDS:
        return {"SLICE": None, "SEEDS": [int(run)], "EPOCHS": 3}
    names = ", ".join(map(str, SEEDS))
    raise ValueError(f"run must be 'smoke', 'baseline' or one of {names}; got {run!r}")


def kernel_slug(run: str) -> str:
    run_params(run)
    return f"finsight-extractor-{run}" if not run.isdigit() else f"finsight-extractor-seed-{run}"


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


# ----------------------------------------------------------------------------- checks
def _finite(x: Any) -> bool:
    return isinstance(x, int | float) and math.isfinite(x)


def check_outputs(metrics: dict[str, Any], weight_files: list[str]) -> list[str]:
    """The smoke criterion: the run ended with scores and weights. Nothing about quality."""
    problems = []
    if not _finite(metrics.get("F1")):
        problems.append("F1 is missing or not a number")
    if not any(name.startswith("model.") for name in weight_files):
        problems.append("no model weights (model.safetensors) in final/")
    if "config.json" not in weight_files:
        problems.append("no config.json in final/")
    return problems


def loss_rises_in_last_epoch(metrics: dict[str, Any]) -> str | None:
    """A warning when the smoothed loss ends the last epoch higher than it began it."""
    epochs = metrics.get("epochs") or 0
    last = [h["loss"] for h in metrics.get("loss_history") or [] if h["epoch"] > epochs - 1]
    if len(last) < 3:
        return None
    third = len(last) // 3
    first, final = sum(last[:third]) / third, sum(last[-third:]) / third
    if final > first:
        return f"smoothed loss rose across the last epoch ({first:.3f} -> {final:.3f})"
    return None


def quality_gate(metrics: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    """A seed passes only if its best epoch beats the zero-shot baseline on dev EM and F1."""
    problems = []
    for name in ("EM", "F1"):
        ours, base = metrics.get(name), baseline.get(name)
        if not (_finite(ours) and _finite(base)):
            problems.append(f"{name} is missing from the run or the baseline")
        elif not ours > base:
            problems.append(f"dev {name} {ours:.4f} does not beat the baseline {base:.4f}")
    return problems


def dev_nvm(rows: list[dict[str, Any]], predictions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Normalized value match on dev: ₹ 300 crore equals ₹ 3,000 million; "" is "no answer".

    A gold span the normalizer cannot read (rare) is compared by exact match instead.
    """
    hits, unparsed = 0, 0
    for row in rows:
        kind = get_field(row["field_id"]).type
        pred = predictions[row["id"]]
        pred_value = None
        if pred["text"]:
            end = pred["start"] + len(pred["text"])
            answer = RawAnswer(pred["text"], 1.0, pred["start"], end)
            pred_value = answer_value(kind, answer, row["context"])
        if not row["answers"]["text"]:
            hits += not pred["text"]
            continue
        text, start = row["answers"]["text"][0], row["answers"]["answer_start"][0]
        gold = answer_value(kind, RawAnswer(text, 1.0, start, start + len(text)), row["context"])
        if gold is None:
            unparsed += 1
            hits += exact_match(pred["text"], text)
        else:
            hits += nvm(pred_value, gold)
    return {"NVM": hits / len(rows) if rows else 0.0, "n": len(rows), "gold_unparsed": unparsed}


# ----------------------------------------------------------------------------- collecting
def _one(root: Path, name: str) -> Path:
    found = sorted(root.rglob(name))
    if not found:
        raise FileNotFoundError(f"{root} has no {name}")
    return found[0]


def _per_epoch(
    metrics: dict[str, Any], rows: list[dict[str, Any]], predictions: dict[str, Any]
) -> list[dict[str, Any]]:
    epochs = metrics.get("per_epoch") or [{"epoch": 0, **metrics}]
    keep = ("EM", "F1", "HasAns_EM", "HasAns_F1", "NoAns_acc")
    out = []
    for e in epochs:
        scores = {k: e[k] for k in keep}
        out.append({"epoch": e["epoch"], **scores, **dev_nvm(rows, predictions[str(e["epoch"])])})
    return out


def collect(
    downloaded: Path, run: str, models_dir: Path, eval_dir: Path, dev_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Check a downloaded run; keep what it earned.

    - smoke: checked, nothing kept.
    - baseline: metrics -> ``eval_results/extractor_baseline.json`` (as the notebook wrote them).
    - seed: weights of the best epoch -> ``models/extractor/seed-<n>/``; metrics, unedited ->
      ``eval_results/extractor_metrics-<n>.json``.
    Baseline and seeds also get ``eval_results/extractor_dev-<run>.json``: EM, F1 and NVM per
    epoch, and for a seed the gate verdict against the baseline.
    """
    params = run_params(run)
    if run == "baseline":
        metrics_file = _one(downloaded, "metrics-baseline.json")
        metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
        predictions = json.loads(_one(downloaded, "predictions-baseline.json").read_text("utf-8"))
        problems = [] if _finite(metrics.get("F1")) else ["F1 is missing or not a number"]
        report = {"run": run, "per_epoch": _per_epoch(metrics, dev_rows, predictions)}
        if not problems:
            eval_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(metrics_file, eval_dir / "extractor_baseline.json")  # never edited
            _write(eval_dir / "extractor_dev-baseline.json", report)
        return {**report, "problems": problems, "warnings": []}

    seed = params["SEEDS"][0]
    metrics_file = _one(downloaded, f"metrics-{seed}.json")
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    finals = [p for p in sorted(downloaded.rglob("final")) if p.parent.name == f"seed-{seed}"]
    final = next((p for p in finals if p.is_dir()), None)
    problems = check_outputs(metrics, [p.name for p in final.iterdir()] if final else [])
    if run == "smoke" or problems:
        return {"run": run, "per_epoch": metrics.get("per_epoch", []), "problems": problems,
                "warnings": []}  # fmt: skip

    baseline_file = eval_dir / "extractor_dev-baseline.json"
    if not baseline_file.exists():
        raise FileNotFoundError("no baseline yet: run `push baseline`, then `fetch baseline`")
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))["per_epoch"][0]
    predictions = json.loads(_one(downloaded, f"predictions-{seed}.json").read_text("utf-8"))
    per_epoch = _per_epoch(metrics, dev_rows, predictions)
    best = next(e for e in per_epoch if e["epoch"] == metrics["best_epoch"])
    problems = quality_gate(best, baseline)
    warning = loss_rises_in_last_epoch(metrics)
    report = {
        "run": run,
        "seed": seed,
        "baseline": baseline,
        "per_epoch": per_epoch,
        "best_epoch": metrics["best_epoch"],
        "passed": not problems,
        "problems": problems,
        "warnings": [warning] if warning else [],
    }
    assert final is not None
    target = models_dir / "extractor" / f"seed-{seed}"
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(final), str(target))  # one copy on disk: the best epoch's weights
    shutil.copyfile(metrics_file, eval_dir / f"extractor_metrics-{seed}.json")  # never edited
    _write(eval_dir / f"extractor_dev-{seed}.json", report)
    return report


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")


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
    parser.add_argument("run", help="smoke | baseline | 13 | 42 | 2026")
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
    dev_file = paths.processed_dir / "weaklabel" / "dev.jsonl"
    dev_rows = [json.loads(x) for x in dev_file.read_text(encoding="utf-8").splitlines() if x]
    result = collect(out, args.run, paths.models_dir, paths.eval_dir, dev_rows)
    if "baseline" in result:
        b = result["baseline"]
        print(f"baseline  EM {b['EM']:.4f}  F1 {b['F1']:.4f}  NVM {b['NVM']:.4f}")
    for e in result["per_epoch"]:
        nvm_text = f"  NVM {e['NVM']:.4f}" if "NVM" in e else ""
        print(f"epoch {e['epoch']}   EM {e['EM']:.4f}  F1 {e['F1']:.4f}{nvm_text}")
    for warning in result["warnings"]:
        print("WARNING:", warning)
    for problem in result["problems"]:
        print("PROBLEM:", problem)
    print("FAILED" if result["problems"] else f"OK: {args.run}")
    if args.run == "smoke":
        shutil.rmtree(out)  # 735 MB of throw-away weights
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
