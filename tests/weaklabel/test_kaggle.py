import ast
import json
from pathlib import Path

import pytest

from finsight.weaklabel.kaggle import (
    NOTEBOOK,
    check_run,
    collect,
    kernel_metadata,
    kernel_slug,
    render_notebook,
    run_params,
    write_kernel,
)


def params_cell(nb: dict) -> str:
    return next(
        "".join(c["source"]) for c in nb["cells"] if "parameters" in c["metadata"].get("tags", [])
    )


def assigned(source: str) -> dict:
    return {
        node.targets[0].id: ast.literal_eval(node.value)  # type: ignore[attr-defined]
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }


def test_smoke_run_is_the_200_slice_one_seed_one_epoch() -> None:
    assert run_params("smoke") == {"SLICE": 200, "SEEDS": [13], "EPOCHS": 1}
    assert run_params("42") == {"SLICE": None, "SEEDS": [42], "EPOCHS": 3}
    assert kernel_slug("smoke") == "finsight-extractor-smoke"
    assert kernel_slug("2026") == "finsight-extractor-seed-2026"
    with pytest.raises(ValueError, match="run must be"):
        run_params("7")


def test_render_rewrites_only_the_named_parameters() -> None:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    before = assigned(params_cell(nb))
    out = render_notebook(nb, run_params("smoke"))
    after = assigned(params_cell(out))
    assert (after["SLICE"], after["SEEDS"], after["EPOCHS"]) == (200, [13], 1)
    untouched = set(before) - {"SLICE", "SEEDS", "EPOCHS"}
    assert {k: after[k] for k in untouched} == {k: before[k] for k in untouched}
    assert assigned(params_cell(nb)) == before  # the input notebook is not changed
    other = [c for c in nb["cells"] if "parameters" not in c["metadata"].get("tags", [])]
    assert [c for c in out["cells"] if "parameters" not in c["metadata"].get("tags", [])] == other
    with pytest.raises(ValueError, match="NO_SUCH"):
        render_notebook(nb, {"NO_SUCH": 1})


def test_kernel_is_private_with_gpu_internet_and_the_dataset() -> None:
    meta = kernel_metadata("akshattmo", "13")
    assert meta["id"] == "akshattmo/finsight-extractor-seed-13"
    assert meta["title"] == "finsight-extractor-seed-13"
    assert (meta["is_private"], meta["enable_gpu"], meta["enable_internet"]) == ("true",) * 3
    assert meta["dataset_sources"] == ["akshattmo/finsight-weaklabel"]
    with pytest.raises(ValueError, match="username"):
        kernel_metadata("AkshatTmO", "13")


def test_write_kernel_makes_the_folder_kaggle_pushes(tmp_path: Path) -> None:
    folder = write_kernel(tmp_path / "k", "akshattmo", "smoke")
    meta = json.loads((folder / "kernel-metadata.json").read_text(encoding="utf-8"))
    nb = json.loads((folder / meta["code_file"]).read_text(encoding="utf-8"))
    assert assigned(params_cell(nb))["SLICE"] == 200
    assert sorted(p.name for p in folder.iterdir()) == ["kernel-metadata.json", "notebook.ipynb"]


GOOD = {"loss_history": [2.1, 1.4, 0.9], "F1": 0.61}
FILES = ["config.json", "model.safetensors", "tokenizer.json"]


def test_a_run_passes_only_when_loss_fell_and_weights_exist() -> None:
    assert check_run(GOOD, FILES) == []
    assert "did not go down" in check_run({**GOOD, "loss_history": [1.0, 1.2]}, FILES)[0]
    assert "fewer than two" in check_run({**GOOD, "loss_history": [1.0]}, FILES)[0]
    assert "fewer than two" in check_run({**GOOD, "loss_history": []}, FILES)[0]
    noisy = [2.0, 2.4, 1.9, 1.5, 1.6, 1.0, 1.2, 0.8, 1.1]  # thirds: 2.1 -> 1.03
    assert check_run({**GOOD, "loss_history": noisy}, FILES) == []
    assert "NaN" in check_run({**GOOD, "loss_history": [1.0, float("nan")]}, FILES)[0]
    assert "F1" in check_run({"loss_history": [2.0, 1.0]}, FILES)[0]
    assert "weights" in check_run(GOOD, ["config.json"])[0]
    assert "config.json" in check_run(GOOD, ["model.safetensors"])[0]


def kaggle_output(root: Path, seed: int, metrics: dict) -> Path:
    final = root / "extractor" / f"seed-{seed}" / "final"
    final.mkdir(parents=True)
    for name in FILES:
        (final / name).write_text("x", encoding="utf-8")
    (root / "extractor" / f"metrics-{seed}.json").write_text(json.dumps(metrics), encoding="utf-8")
    return root


def test_collect_puts_weights_in_models_and_metrics_in_eval_results(tmp_path: Path) -> None:
    out = kaggle_output(tmp_path / "out", 42, GOOD)
    result = collect(out, "42", tmp_path / "models", tmp_path / "eval")
    assert result["problems"] == []
    kept = tmp_path / "models" / "extractor" / "seed-42"
    assert sorted(p.name for p in kept.iterdir()) == FILES
    saved = json.loads((tmp_path / "eval" / "extractor_metrics-42.json").read_text("utf-8"))
    assert saved == GOOD  # copied as written by the notebook


def test_collect_keeps_nothing_from_a_smoke_or_failed_run(tmp_path: Path) -> None:
    models, results = tmp_path / "m", tmp_path / "e"
    smoke = collect(kaggle_output(tmp_path / "s", 13, GOOD), "smoke", models, results)
    assert smoke["problems"] == []
    bad = {**GOOD, "loss_history": [1.0, 3.0]}
    failed = collect(kaggle_output(tmp_path / "f", 13, bad), "13", tmp_path / "m", tmp_path / "e")
    assert failed["problems"]
    assert not (tmp_path / "m").exists()
    assert not (tmp_path / "e").exists()
    with pytest.raises(FileNotFoundError):
        collect(tmp_path / "s", "42", tmp_path / "m", tmp_path / "e")
