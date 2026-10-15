"""Classifier runs on Kaggle (C2.4): split manifests, kernel folders and the seed summary (E16).

The training itself is the notebook ``notebooks/b2_classifier_base_kaggle.ipynb``; this module
holds the testable parts around it:

* ``ipo_ids_of`` / ``split_manifests``: which IPOs the classifier's train and dev rows come from
  (the time split, C-ADR-02: only ``train``-slice documents may appear).
* ``kernel_folder``: the folder ``kaggle kernels push -p`` uploads for one run.
* ``summarise``: mean and spread of the seeds' dev macro-F1, the best seed (chosen on dev only)
  and the gate against the TF-IDF baseline (E16).
"""

from __future__ import annotations

import json
import re
import statistics
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from finsight.risks.classify import Example

DATASET = "finsight-risk-classifier"
SEEDS = (13, 42, 2026)
CODE_FILE = "notebook.ipynb"
_USERNAME = re.compile(r"^[a-z0-9][a-z0-9-]{2,}$")


def ipo_id_of(risk_id: str) -> str:
    """``<ipo_id>#<rid>`` -> ``<ipo_id>`` (the form ``export_teacher_input`` writes)."""
    return risk_id.split("#", 1)[0]


def ipo_ids_of(examples: Iterable[Example]) -> list[str]:
    """Sorted unique IPO ids behind a set of examples."""
    return sorted({ipo_id_of(e.risk_id) for e in examples})


def run_params(run: str) -> dict[str, Any]:
    """``smoke`` or one seed -> the parameters-cell values of the base notebook."""
    if run == "smoke":
        return {"SEEDS": [SEEDS[0]], "SMOKE": True}
    if run.isdigit() and int(run) in SEEDS:
        return {"SEEDS": [int(run)], "SMOKE": False}
    raise ValueError(f"run must be 'smoke' or one of {', '.join(map(str, SEEDS))}; got {run!r}")


def kernel_slug(run: str) -> str:
    """Kaggle kernel slug of a run (title and slug must match)."""
    run_params(run)
    return "finsight-clf-smoke" if run == "smoke" else f"finsight-clf-seed-{run}"


def kernel_folder(folder: Path, notebook: Path, username: str, run: str) -> Path:
    """Rendered notebook and ``kernel-metadata.json`` for ``kaggle kernels push -p folder``."""
    from finsight.weaklabel.kaggle import render_notebook

    if not _USERNAME.match(username):
        raise ValueError(f"username {username!r} is not a Kaggle username (lowercase, digits, -)")
    nb = render_notebook(json.loads(notebook.read_text(encoding="utf-8")), run_params(run))
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
        "dataset_sources": [f"{username}/{DATASET}"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / CODE_FILE).write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8", newline="\n")
    (folder / "kernel-metadata.json").write_text(
        json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    return folder


def summarise(
    metrics: Sequence[dict[str, Any]], baseline: dict[str, Any] | None = None
) -> dict[str, Any]:
    """E16 for the base model: per-seed dev macro-F1, mean and spread, best seed, baseline gate.

    The best seed is picked on **dev** only; gold-150 never chooses anything. Smoke runs are
    refused: a summary over a 200-row slice would be mistaken for a result.
    """
    real = [m for m in metrics if not m.get("smoke") and m.get("task", "category") == "category"]
    if not real:
        raise ValueError("no non-smoke metrics to summarise")
    f1 = {int(m["seed"]): float(m["dev"]["macro_f1"]) for m in real}
    best = max(f1, key=lambda s: (f1[s], -s))
    out: dict[str, Any] = {
        "model": real[0]["model"],
        "n_seeds": len(f1),
        "seeds": sorted(f1),
        "dev_macro_f1_by_seed": {str(s): round(f1[s], 4) for s in sorted(f1)},
        "dev_macro_f1_mean": round(statistics.fmean(f1.values()), 4),
        "dev_macro_f1_sd": round(statistics.stdev(f1.values()), 4) if len(f1) > 1 else None,
        "best_seed": best,
        "selected_on": "dev macro-F1 (gold-150 is for the final report only)",
        "label_source": "teacher (AI labels); see docs/phase2/datasheets/teacher_outputs.md",
        "n_train": real[0].get("n_train"),
        "n_dev": real[0].get("n_dev"),
    }
    if len(f1) == 1:
        out["note"] = "single seed: no spread can be reported"
    tests = {int(m["seed"]): m["test"] for m in real if m.get("test")}
    if tests:
        out["test_label_source"] = "human:akshat (gold-150, test-slice IPOs)"
        out["test_macro_f1_by_seed"] = {str(s): round(t["macro_f1"], 4) for s, t in tests.items()}
        out["test_macro_f1_mean"] = _mean(t["macro_f1"] for t in tests.values())
        out["test_best_seed"] = tests.get(best)
    if baseline is not None:
        base = float(baseline["dev"]["macro_f1"])
        out["tfidf_dev_macro_f1"] = round(base, 4)
        out["beats_tfidf"] = out["dev_macro_f1_mean"] > base
    return out


BAND_KEYS = ("macro_f1", "mae", "within_1", "severe_recall", "severe_precision")


def _mean(xs: Iterable[float | None]) -> float | None:
    vals = [float(x) for x in xs if x is not None]
    return round(statistics.fmean(vals), 4) if vals else None


def summarise_band(metrics: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Seriousness bands (1, 2, 3, 4 = severe): per-seed and mean dev scores (macro-F1, MAE,
    within-1, severe recall / precision), the best seed on dev macro-F1 and its test scores.

    Test bands are the teacher's (gold-150 has no human seriousness label), so test numbers are
    agreement with the teacher on held-out IPOs.
    """
    real = [m for m in metrics if not m.get("smoke") and m.get("task") == "band"]
    if not real:
        raise ValueError("no non-smoke band metrics to summarise")
    by_seed = {int(m["seed"]): m for m in real}
    best = max(by_seed, key=lambda s: (by_seed[s]["dev"]["macro_f1"], -s))
    out: dict[str, Any] = {
        "model": real[0]["model"],
        "bands": "1, 2, 3, 4 = severe (levels 4 and 5 merged)",
        "n_seeds": len(by_seed),
        "seeds": sorted(by_seed),
        "dev_by_seed": {str(s): {k: m["dev"].get(k) for k in BAND_KEYS} for s, m in
                        sorted(by_seed.items())},
        "dev_mean": {k: _mean(m["dev"].get(k) for m in real) for k in BAND_KEYS},
        "best_seed": best,
        "selected_on": "dev band macro-F1 (gold-150 is for the final report only)",
        "label_source": "teacher (AI labels); see docs/phase2/datasheets/teacher_outputs.md",
        "n_train": real[0].get("n_train"),
        "n_dev": real[0].get("n_dev"),
    }  # fmt: skip
    test = by_seed[best].get("test")
    if test:
        out["test_best_seed"] = {k: test.get(k) for k in (*BAND_KEYS, "severe_support", "n")}
        out["test_label_source"] = "teacher:gemma-4-31b-it band on gold-150 (no human label)"
    if len(by_seed) == 1:
        out["note"] = "single seed: no spread can be reported"
    return out


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a result file (LF, indented, trailing newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
