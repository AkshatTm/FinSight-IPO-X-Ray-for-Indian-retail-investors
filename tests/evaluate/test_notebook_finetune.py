"""Structural checks on the Kaggle notebook (it is never run here; Akshat runs it on Kaggle)."""

import ast
import json
from pathlib import Path

import pytest

NB = Path(__file__).resolve().parents[2] / "notebooks" / "01_finetune_extractor.ipynb"


@pytest.fixture(scope="module")
def nb() -> dict:
    return json.loads(NB.read_text(encoding="utf-8"))


def code_cells(nb: dict) -> list[str]:
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_notebook_has_no_outputs_and_parses(nb: dict) -> None:
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None
    for src in code_cells(nb):
        ast.parse(src)


def test_parameters_cell_exposes_the_knobs(nb: dict) -> None:
    tagged = [
        "".join(c["source"]) for c in nb["cells"] if "parameters" in c["metadata"].get("tags", [])
    ]
    assert len(tagged) == 1
    names = {
        n.id
        for n in ast.walk(ast.parse(tagged[0]))
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
    }
    assert {
        "MODEL",
        "SEEDS",
        "SLICE",
        "EPOCHS",
        "LEARNING_RATE",
        "MAX_LEN",
        "STRIDE",
        "RESUME",
    } <= names
    assert "[13, 42, 2026]" in tagged[0]


def test_notebook_metrics_mirror_the_evaluate_module(nb: dict) -> None:
    """The notebook's own SQuAD scorer must agree with finsight.evaluate.metrics."""
    from finsight.evaluate.metrics import exact_match, token_f1

    ns: dict = {}
    src = next(s for s in code_cells(nb) if "def normalize_text" in s)
    head = src.split("def postprocess")[0]
    exec("import re, string\nfrom collections import Counter\n" + head, ns)
    pairs = [
        ("The Fresh Issue", "fresh  issue."),
        ("kfin technologies", "kfin technologies limited"),
        ("", ""),
        ("axis", "jm financial"),
        ("", "x"),
    ]
    for p, g in pairs:
        assert ns["exact_match"](p, g) == exact_match(p, g)
        assert ns["token_f1"](p, g) == pytest.approx(token_f1(p, g))
