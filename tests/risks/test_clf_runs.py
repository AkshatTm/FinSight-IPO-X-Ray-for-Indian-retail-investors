import importlib.util
import json
from pathlib import Path

import pytest

from finsight.risks.classify import Example
from finsight.risks.clf_runs import (
    ipo_id_of,
    ipo_ids_of,
    kernel_folder,
    kernel_slug,
    run_params,
    summarise,
)

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "b2_classifier_base_kaggle.ipynb"


def metrics(seed: int, f1: float, smoke: bool = False) -> dict:
    return {"seed": seed, "model": "deberta", "smoke": smoke, "n_train": 100, "n_dev": 10,
            "dev": {"macro_f1": f1}}  # fmt: skip


def test_ipo_ids_come_from_the_risk_id_prefix() -> None:
    assert ipo_id_of("ather-2025#r12") == "ather-2025"
    rows = [Example("a-2025#1", "A", "t", "financial"), Example("a-2025#2", "A", "t", "financial"),
            Example("b-2024#1", "B", "t", "financial")]  # fmt: skip
    assert ipo_ids_of(rows) == ["a-2025", "b-2024"]


def test_run_params_and_slugs() -> None:
    assert run_params("smoke") == {"SEEDS": [13], "SMOKE": True}
    assert run_params("42") == {"SEEDS": [42], "SMOKE": False}
    assert kernel_slug("smoke") == "finsight-clf-smoke"
    assert kernel_slug("2026") == "finsight-clf-seed-2026"
    with pytest.raises(ValueError, match="run must be"):
        run_params("7")


def test_kernel_folder_injects_seed_and_smoke(tmp_path: Path) -> None:
    folder = kernel_folder(tmp_path / "k", NOTEBOOK, "someone", "42")
    meta = json.loads((folder / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert meta["id"] == "someone/finsight-clf-seed-42"
    assert meta["is_private"] == "true"
    assert meta["dataset_sources"] == ["someone/finsight-risk-classifier"]
    nb = json.loads((folder / "notebook.ipynb").read_text(encoding="utf-8"))
    params = next(
        "".join(c["source"]) for c in nb["cells"] if "parameters" in c["metadata"].get("tags", [])
    )
    assert "SEEDS = [42]" in params
    assert "SMOKE = False" in params
    with pytest.raises(ValueError, match="Kaggle username"):
        kernel_folder(tmp_path / "k2", NOTEBOOK, "Bad Name", "42")


def test_summarise_picks_best_seed_on_dev_and_gates_on_tfidf() -> None:
    res = summarise([metrics(13, 0.70), metrics(42, 0.74), metrics(2026, 0.72)],
                    {"dev": {"macro_f1": 0.65}})  # fmt: skip
    assert res["best_seed"] == 42
    assert res["dev_macro_f1_mean"] == 0.72
    assert res["dev_macro_f1_sd"] == 0.02
    assert res["beats_tfidf"] is True
    worse = summarise([metrics(13, 0.60)], {"dev": {"macro_f1": 0.65}})
    assert worse["beats_tfidf"] is False
    assert worse["dev_macro_f1_sd"] is None
    assert "single seed" in worse["note"]


def test_summarise_refuses_smoke_only() -> None:
    with pytest.raises(ValueError, match="no non-smoke"):
        summarise([metrics(13, 0.9, smoke=True)])
    res = summarise([metrics(13, 0.9, smoke=True), metrics(42, 0.5)])
    assert res["seeds"] == [42]


def test_script_manifests_only_train_slice_ipos(tmp_path: Path, monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "clf_kaggle", ROOT / "scripts/classifier_kaggle.py"
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    split = tmp_path / "split"
    split.mkdir()
    for name, ids in (("train", ["a-2024", "b-2024"]), ("dev", ["c-2025"])):
        with (split / f"{name}.jsonl").open("w", encoding="utf-8") as fh:
            for i in ids:
                fh.write(json.dumps({"risk_id": f"{i}#1", "company": i, "text": "x",
                                     "label": "financial"}) + "\n")  # fmt: skip
    monkeypatch.setattr(mod, "SPLIT_DIR", split)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    mod.cmd_manifests()
    train = json.loads((tmp_path / "data/manifests/classifier_train.json").read_text("utf-8"))
    assert train["kind"] == "train"
    assert train["ipo_ids"] == ["a-2024", "b-2024"]
    assert (tmp_path / "data/manifests/classifier_dev.json").exists()
