import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from finsight.risks import simplify

ROOT = Path(__file__).resolve().parents[2]


def load() -> ModuleType:
    path = ROOT / "scripts" / "make_student_notebook.py"
    spec = importlib.util.spec_from_file_location("make_student_notebook", path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cell(nb: dict[str, Any], tag: str) -> str:
    [c] = [c for c in nb["cells"] if tag in c["metadata"].get("tags", [])]
    return "".join(c["source"])


def test_committed_notebook_matches_the_generator_and_compiles() -> None:
    committed = json.loads(
        (ROOT / "notebooks" / "b2_student_qlora_kaggle.ipynb").read_text("utf-8")
    )
    assert committed == load().build(), "run: uv run python scripts/make_student_notebook.py"
    for c in committed["cells"]:
        if c["cell_type"] == "code":
            compile("".join(c["source"]), "student", "exec")


def test_prompt_cell_and_b03_parameters() -> None:
    nb = load().build()
    ns: dict[str, Any] = {}
    exec(cell(nb, "student-prompt"), ns)
    assert ns["INSTRUCTIONS"] == simplify.INSTRUCTIONS
    assert ns["PROMPT_VERSION"] == simplify.PROMPT_VERSION
    params: dict[str, Any] = {}
    exec(cell(nb, "parameters"), params)
    assert params["LEARNING_RATE"] == 2e-4
    assert params["MAX_SEQ"] == 1024
    assert params["SAVE_STEPS"] == 200
    assert params["SMOKE"] is False
    assert "r=16, lora_alpha=32, lora_dropout=0.05" in "".join(nb["cells"][-1]["source"])


class FakeTokenizer:
    """Character-level stand-in with a ChatML-like template."""

    def apply_chat_template(
        self,
        msgs: list[dict[str, str]],
        tokenize: bool = False,
        add_generation_prompt: bool = False,
    ) -> str:
        text = "".join(f"<{m['role']}>{m['content']}</>" for m in msgs)
        return text + ("<assistant>" if add_generation_prompt else "")

    def __call__(self, text: str, add_special_tokens: bool = False) -> dict[str, list[int]]:
        return {"input_ids": [ord(ch) for ch in text]}


def test_only_answer_tokens_carry_loss_and_long_rows_are_skipped() -> None:
    ns: dict[str, Any] = {}
    exec(cell(load().build(), "student-prep"), ns)
    row = simplify.to_chat(
        {"risk_id": "r", "original": "Debt may rise.", "simple": "Debt may go up."}
    )
    enc = ns["encode_row"](FakeTokenizer(), row, 10_000)
    prompt_len = sum(1 for x in enc["labels"] if x == -100)
    answer = "".join(chr(t) for t in enc["labels"][prompt_len:])
    assert answer == "Debt may go up.</>"
    assert ns["encode_row"](FakeTokenizer(), row, 20) is None
    ids, labels, mask = ns["collate"]([enc, {"input_ids": [1], "labels": [1]}], 0)
    assert len(ids[1]) == len(ids[0])
    assert labels[1][1:] == [-100] * (len(ids[0]) - 1)
    assert mask[1][:2] == [1, 0]
