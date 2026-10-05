"""Risk classifier on Kaggle: manifests, dataset, push/status/fetch and the seed summary (C2.4).

    uv run python -m finsight.risks.classify split                 # train/dev by company
    uv run python scripts/classifier_kaggle.py manifests           # time-split manifests for both sides
    uv run python scripts/classifier_kaggle.py dataset --username <you>   # private dataset (create/version)
    uv run python scripts/classifier_kaggle.py push smoke --username <you>
    uv run python scripts/classifier_kaggle.py status smoke --username <you>
    uv run python scripts/classifier_kaggle.py fetch smoke --username <you>
    uv run python scripts/classifier_kaggle.py push 13 --username <you>      # then 42, 2026
    uv run python scripts/classifier_kaggle.py summary             # -> eval_results/b/classifier_base.json (E16)

Official ``kaggle`` CLI only (through ``uvx``); no token is read here. Nothing trains on the laptop.
Weights land in ``models/risk_classifier/seed-<n>/`` (gitignored); only the result JSON is committed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.risks.classify import Example  # noqa: E402
from finsight.risks.clf_runs import (  # noqa: E402
    DATASET,
    ipo_ids_of,
    kernel_folder,
    kernel_slug,
    summarise,
    write_json,
)
from finsight.risks.teacher_run import read_jsonl  # noqa: E402

SPLIT_DIR = ROOT / "data" / "processed" / "kaggle" / "risk-classifier"
WORK = ROOT / "data" / "processed" / "kaggle"
NOTEBOOK = ROOT / "notebooks" / "b2_classifier_base_kaggle.ipynb"
MODELS = ROOT / "models" / "risk_classifier"
RESULT = ROOT / "eval_results" / "b" / "classifier_base.json"
BASELINE = ROOT / "eval_results" / "b" / "classifier_tfidf.json"


def kaggle(*args: str) -> int:
    """Run the official Kaggle CLI through uvx."""
    exe = shutil.which("uvx")
    if exe is None:
        raise FileNotFoundError("uvx is not on PATH (install uv)")
    return subprocess.run([exe, "kaggle", *args], check=False).returncode


def cmd_manifests() -> None:
    """Write ``classifier_train`` / ``classifier_dev`` manifests (kind train: no test or bench)."""
    from finsight.splits import Manifest, file_sha256, write_manifest

    for name in ("train", "dev"):
        path = SPLIT_DIR / f"{name}.jsonl"
        ids = ipo_ids_of(Example(**r) for r in read_jsonl(path))
        write_manifest(
            Manifest(artefact=f"classifier_{name}", kind="train", ipo_ids=ids,
                     sha256=file_sha256(path), written_by="scripts/classifier_kaggle.py",
                     note="teacher-labelled risks, split by company"),
            ROOT / "data" / "manifests",
        )  # fmt: skip
        print(f"classifier_{name}: {len(ids)} IPOs")


def cmd_dataset(username: str) -> int:
    """Create (first time) or version the private dataset from the split folder."""
    meta = {
        "title": DATASET,
        "id": f"{username}/{DATASET}",
        "licenses": [{"name": "other"}],
        "isPrivate": True,
    }
    (SPLIT_DIR / "dataset-metadata.json").write_text(json.dumps(meta, indent=1) + "\n", "utf-8")
    code = kaggle("datasets", "create", "-p", str(SPLIT_DIR))
    if code != 0:  # already exists
        code = kaggle("datasets", "version", "-p", str(SPLIT_DIR), "-m", "new split")
    return code


def cmd_fetch(username: str, run: str) -> int:
    """Download a finished run's output and keep its metrics, predictions and weights."""
    out = WORK / "output" / kernel_slug(run)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    code = kaggle("kernels", "output", f"{username}/{kernel_slug(run)}", "-p", str(out), "-o", "-q")
    if code != 0:
        return code
    for f in sorted(out.rglob("metrics-*.json")) + sorted(out.rglob("dev-predictions-*.json")):
        MODELS.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, MODELS / f.name)
    for seed_dir in out.rglob("seed-*"):
        if seed_dir.is_dir():
            shutil.copytree(seed_dir, MODELS / seed_dir.name, dirs_exist_ok=True)
    print("copied metrics, dev predictions and weights to", MODELS)
    return 0


def cmd_summary() -> None:
    """E16 for the base model from every real ``metrics-<seed>.json`` in the models folder."""
    metrics = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(MODELS.glob("metrics-*.json"))
    ]
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None
    result = summarise(metrics, baseline)
    write_json(RESULT, result)
    print(json.dumps(result, indent=1))


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "command", choices=["manifests", "dataset", "push", "status", "fetch", "summary"]
    )
    ap.add_argument("run", nargs="?", default="smoke", help="smoke | 13 | 42 | 2026")
    ap.add_argument("--username", default="")
    a = ap.parse_args(argv)
    if a.command == "manifests":
        cmd_manifests()
        return 0
    if a.command == "summary":
        cmd_summary()
        return 0
    if not a.username:
        ap.error("this command needs --username (your Kaggle username)")
    user = a.username.lower()
    if a.command == "dataset":
        return cmd_dataset(user)
    if a.command == "fetch":
        return cmd_fetch(user, a.run)
    if a.command == "status":
        return kaggle("kernels", "status", f"{user}/{kernel_slug(a.run)}")
    folder = kernel_folder(WORK / "kernels" / kernel_slug(a.run), NOTEBOOK, user, a.run)
    return kaggle("kernels", "push", "-p", str(folder), "--accelerator", "NvidiaTeslaT4")


if __name__ == "__main__":
    sys.exit(main())
