import ast
import json
from pathlib import Path

import pytest

from finsight.weaklabel.kaggle import (
    NOTEBOOK,
    check_outputs,
    collect,
    dev_nvm,
    kernel_metadata,
    kernel_slug,
    loss_rises_in_last_epoch,
    quality_gate,
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


def test_baseline_run_trains_nothing() -> None:
    assert run_params("baseline") == {"SLICE": None, "ZERO_SHOT": True}
    assert kernel_slug("baseline") == "finsight-extractor-baseline"
    nb = render_notebook(json.loads(NOTEBOOK.read_text(encoding="utf-8")), run_params("baseline"))
    assert assigned(params_cell(nb))["ZERO_SHOT"] is True


FILES = ["config.json", "model.safetensors", "tokenizer.json"]


def test_smoke_passes_on_outputs_alone() -> None:
    assert check_outputs({"F1": 0.6}, FILES) == []
    assert "F1" in check_outputs({}, FILES)[0]
    assert "F1" in check_outputs({"F1": float("nan")}, FILES)[0]
    assert "weights" in check_outputs({"F1": 0.6}, ["config.json"])[0]
    assert "config.json" in check_outputs({"F1": 0.6}, ["model.safetensors"])[0]


def test_a_seed_must_beat_the_baseline_on_em_and_f1() -> None:
    base = {"EM": 0.70, "F1": 0.75}
    assert quality_gate({"EM": 0.80, "F1": 0.85}, base) == []
    assert "EM" in quality_gate({"EM": 0.70, "F1": 0.85}, base)[0]  # equal is not better
    assert "F1" in quality_gate({"EM": 0.80, "F1": 0.74}, base)[0]
    assert len(quality_gate({"EM": 0.1, "F1": 0.1}, base)) == 2
    assert "missing" in quality_gate({"F1": 0.9}, base)[0]


def history(losses: list[float], epoch: float) -> list[dict]:
    return [{"step": i, "epoch": epoch + i / 100, "loss": x} for i, x in enumerate(losses)]


def test_rising_smoothed_loss_in_the_last_epoch_is_flagged() -> None:
    early = history([2.0, 1.0, 0.5], 0.1)
    falling = {"epochs": 3, "loss_history": early + history([0.5, 0.4, 0.3, 0.3, 0.2, 0.2], 2.1)}
    rising = {"epochs": 3, "loss_history": early + history([0.2, 0.2, 0.3, 0.3, 0.5, 0.6], 2.1)}
    assert loss_rises_in_last_epoch(falling) is None
    assert "rose" in (loss_rises_in_last_epoch(rising) or "")
    assert loss_rises_in_last_epoch({"epochs": 3, "loss_history": early}) is None  # too few


def dev_row(i: int, field: str, context: str, answer: str | None) -> dict:
    answers = {"text": [], "answer_start": []}
    if answer:
        answers = {"text": [answer], "answer_start": [context.index(answer)]}
    return {"id": f"r{i}", "field_id": field, "context": context, "answers": answers}


FRESH = "The Fresh Issue is of ₹ 3,000 million in total."
REGISTRAR = "Registrar to the Offer: KFin Technologies Limited"
DEV = [
    dev_row(0, "fresh_issue_size", FRESH, "₹ 3,000 million"),
    dev_row(1, "registrar", REGISTRAR, "KFin Technologies Limited"),
    dev_row(2, "face_value", "Our revenue grew in Fiscal 2019.", None),
]


def pred(row: dict, text: str) -> dict:
    return {"text": text, "start": row["context"].index(text) if text else -1}


def test_dev_nvm_reads_values_not_strings() -> None:
    right = {
        "r0": pred(DEV[0], "3,000"),  # bare number: unit and rupee sign sit around the span
        "r1": pred(DEV[1], "KFin Technologies Limited"),
        "r2": pred(DEV[2], ""),
    }
    assert dev_nvm(DEV, right) == {"NVM": 1.0, "n": 3, "gold_unparsed": 0}
    wrong = {
        "r0": pred(DEV[0], ""),  # missed an answer
        "r1": pred(DEV[1], "KFin"),  # a different name
        "r2": pred(DEV[2], "2019"),  # answered where there is nothing
    }
    assert dev_nvm(DEV, wrong)["NVM"] == 0.0


def kaggle_output(root: Path, seed: int, metrics: dict, predictions: dict) -> Path:
    final = root / "extractor" / f"seed-{seed}" / "final"
    final.mkdir(parents=True)
    for name in FILES:
        (final / name).write_text("x", encoding="utf-8")
    out = root / "extractor"
    (out / f"metrics-{seed}.json").write_text(json.dumps(metrics), encoding="utf-8")
    (out / f"predictions-{seed}.json").write_text(json.dumps(predictions), encoding="utf-8")
    return root


def baseline_output(root: Path, em: float, f1: float) -> Path:
    out = root / "extractor"
    out.mkdir(parents=True)
    scores = {"EM": em, "F1": f1, "HasAns_EM": 0.5, "HasAns_F1": 0.5, "NoAns_acc": 0.9}
    (out / "metrics-baseline.json").write_text(json.dumps(scores), encoding="utf-8")
    all_wrong = {r["id"]: {"text": "", "start": -1} for r in DEV}
    (out / "predictions-baseline.json").write_text(json.dumps({"0": all_wrong}), encoding="utf-8")
    return root


def seed_metrics(em: float, f1: float) -> dict:
    scores = {"HasAns_EM": 0.9, "HasAns_F1": 0.9, "NoAns_acc": 0.9}
    first, second = {"epoch": 1, "EM": 0.1, "F1": 0.1}, {"epoch": 2, "EM": em, "F1": f1}
    epochs = [{**first, **scores}, {**second, **scores}]
    return {"EM": em, "F1": f1, **scores, "epochs": 2, "best_epoch": 2, "per_epoch": epochs,
            "loss_history": history([1.0, 0.5, 0.4], 1.1)}  # fmt: skip


RIGHT = {r["id"]: pred(r, r["answers"]["text"][0] if r["answers"]["text"] else "") for r in DEV}
PREDICTIONS = {"1": RIGHT, "2": RIGHT}


def test_collect_baseline_then_a_passing_seed(tmp_path: Path) -> None:
    models, results = tmp_path / "models", tmp_path / "eval"
    base = collect(baseline_output(tmp_path / "b", 0.70, 0.75), "baseline", models, results, DEV)
    assert base["problems"] == []
    saved = json.loads((results / "extractor_baseline.json").read_text("utf-8"))
    assert saved["EM"] == 0.70  # the notebook's file, copied as written
    assert base["per_epoch"][0]["NVM"] == pytest.approx(1 / 3)  # only the no-answer row is right

    out = kaggle_output(tmp_path / "out", 42, seed_metrics(0.8, 0.85), PREDICTIONS)
    result = collect(out, "42", models, results, DEV)
    assert result["passed"] is True
    assert result["warnings"] == []
    assert result["baseline"]["EM"] == 0.70
    assert [e["NVM"] for e in result["per_epoch"]] == [1.0, 1.0]
    kept = models / "extractor" / "seed-42"
    assert sorted(p.name for p in kept.iterdir()) == FILES
    assert not (out / "extractor" / "seed-42" / "final").exists()  # moved: one copy on disk
    assert json.loads((results / "extractor_metrics-42.json").read_text("utf-8"))["EM"] == 0.8
    assert json.loads((results / "extractor_dev-42.json").read_text("utf-8"))["passed"] is True


def test_collect_reports_a_seed_that_does_not_beat_the_baseline(tmp_path: Path) -> None:
    models, results = tmp_path / "models", tmp_path / "eval"
    collect(baseline_output(tmp_path / "b", 0.90, 0.95), "baseline", models, results, DEV)
    out = kaggle_output(tmp_path / "out", 13, seed_metrics(0.8, 0.85), PREDICTIONS)
    result = collect(out, "13", models, results, DEV)
    assert result["passed"] is False
    assert len(result["problems"]) == 2
    assert json.loads((results / "extractor_dev-13.json").read_text("utf-8"))["passed"] is False


def test_collect_needs_the_baseline_and_keeps_nothing_from_a_smoke_run(tmp_path: Path) -> None:
    models, results = tmp_path / "m", tmp_path / "e"
    out = kaggle_output(tmp_path / "s", 13, seed_metrics(0.8, 0.85), PREDICTIONS)
    assert collect(out, "smoke", models, results, DEV)["problems"] == []
    assert not models.exists()
    assert not results.exists()
    with pytest.raises(FileNotFoundError, match="baseline"):
        collect(out, "13", models, results, DEV)
