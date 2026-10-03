import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from finsight.risks import teacher

ROOT = Path(__file__).resolve().parents[2]


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "make_teacher_notebook", ROOT / "scripts" / "make_teacher_notebook.py"
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cell(nb: dict[str, Any], tag: str) -> str:
    [c] = [c for c in nb["cells"] if tag in c["metadata"].get("tags", [])]
    return "".join(c["source"])


def test_committed_notebook_matches_the_generator() -> None:
    committed = json.loads((ROOT / "notebooks" / "b2_teacher_kaggle.ipynb").read_text("utf-8"))
    assert committed == load_script().build(), "run: uv run python scripts/make_teacher_notebook.py"


def test_prompt_cell_reproduces_the_tested_prompt() -> None:
    ns: dict[str, Any] = {}
    exec(cell(load_script().build(), "teacher-prompt"), ns)
    assert ns["SYSTEM"] == teacher.SYSTEM
    assert ns["OUTPUT_SCHEMA"] == teacher.OUTPUT_SCHEMA
    assert ns["PROMPT_VERSION"] == teacher.PROMPT_VERSION
    assert ns["messages"]("T", "body") == teacher.messages("T", "body")
    assert ns["messages"]("", "body") == teacher.messages("", "body")


def test_run_cell_is_the_tested_module_and_every_cell_compiles() -> None:
    nb = load_script().build()
    assert cell(nb, "teacher-run") == (ROOT / "src/finsight/risks/teacher_run.py").read_text(
        "utf-8"
    )
    for c in nb["cells"]:
        if c["cell_type"] == "code":
            compile("".join(c["source"]), "cell", "exec")


def test_kernel_folder_renders_the_limit(tmp_path: Path) -> None:
    mod = load_script()
    folder = mod.kernel_folder("pilot", "someone", tmp_path / "k")
    nb = json.loads((folder / "notebook.ipynb").read_text("utf-8"))
    assert "LIMIT = 500\n" in cell(nb, "parameters")
    meta = json.loads((folder / "kernel-metadata.json").read_text("utf-8"))
    assert meta["id"] == "someone/finsight-teacher-pilot"
    assert meta["dataset_sources"] == ["someone/finsight-teacher-risks"]
    assert meta["is_private"] == "true"
