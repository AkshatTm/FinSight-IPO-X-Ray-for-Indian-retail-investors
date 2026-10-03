import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cell(nb: dict[str, Any], tag: str) -> str:
    [c] = [c for c in nb["cells"] if tag in c["metadata"].get("tags", [])]
    return "".join(c["source"])


@pytest.mark.parametrize(
    "name", ["b2_classifier_base_kaggle.ipynb", "b2_classifier_large_kaggle.ipynb"]
)
def test_committed_notebooks_match_the_generator(name: str) -> None:
    gen = load("make_classifier_notebooks")
    committed = json.loads((ROOT / "notebooks" / name).read_text("utf-8"))
    assert committed == gen.build(name), "run: uv run python scripts/make_classifier_notebooks.py"
    metrics = (ROOT / "src/finsight/risks/clf_metrics.py").read_text("utf-8")
    assert cell(committed, "clf-metrics") == metrics
    for c in committed["cells"]:
        if c["cell_type"] == "code":
            compile("".join(c["source"]), name, "exec")


def test_parameters_follow_b03() -> None:
    gen = load("make_classifier_notebooks")
    base: dict[str, Any] = {}
    exec(cell(gen.build("b2_classifier_base_kaggle.ipynb"), "parameters"), base)
    large: dict[str, Any] = {}
    exec(cell(gen.build("b2_classifier_large_kaggle.ipynb"), "parameters"), large)
    assert base["SEEDS"] == [13, 42, 2026]
    assert base["LEARNING_RATE"] == 2e-5
    assert base["MAX_LEN"] == large["MAX_LEN"] == 384
    assert large["SEEDS"] == [42]
    assert large["LEARNING_RATE"] == 1e-5
    assert base["SMOKE"] is False


@pytest.mark.local
def test_onnx_export_matches_pytorch(tmp_path: Path) -> None:
    """Needs torch + transformers + a downloaded tiny model (local session)."""
    pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    exp = load("export_onnx_classifier")
    src = tmp_path / "final"
    name = "hf-internal-testing/tiny-random-DebertaV2ForSequenceClassification"
    labels = ["financial", "regulatory"]
    model = transformers.AutoModelForSequenceClassification.from_pretrained(
        name, num_labels=2, id2label=dict(enumerate(labels)), ignore_mismatched_sizes=True
    )
    model.save_pretrained(src)
    transformers.AutoTokenizer.from_pretrained(name).save_pretrained(src)
    dev = tmp_path / "dev.jsonl"
    dev.write_text(
        "\n".join(
            json.dumps({"text": f"risk number {i}", "label": labels[i % 2]}) for i in range(20)
        ),
        encoding="utf-8",
    )
    out = exp.export(src, tmp_path / "onnx")
    result = exp.check(src, out, dev)
    assert result["agreement"] >= 0.9
