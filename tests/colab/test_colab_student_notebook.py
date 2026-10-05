"""C2.5: the Colab student notebook (static checks; training itself needs a GPU)."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NB = ROOT / "notebooks" / "colab" / "c2_student.ipynb"


def cells() -> list[dict]:
    return json.loads(NB.read_text(encoding="utf-8"))["cells"]


def source(c: dict) -> str:
    return "".join(c["source"])


def test_every_code_cell_parses() -> None:
    for c in cells():
        if c["cell_type"] == "code":
            ast.parse(source(c))


def test_parameters_cell_has_precision_and_smoke_defaults() -> None:
    params = next(source(c) for c in cells() if "parameters" in c["metadata"].get("tags", []))
    assert 'PRECISION = "bf16"' in params
    assert "SMOKE = True" in params  # a first run is always the cheap one
    assert "UPLOAD = False" in params


def test_never_ships_merged_weights() -> None:
    body = "\n".join(source(c) for c in cells() if c["cell_type"] == "code")
    assert "push_to_hub" not in body
    assert "rmtree(out / " in body  # the merged fp16 folder is deleted after the GGUF
    assert "Q4_K_M" in body


def test_nf4_path_uses_fp16_and_bf16_path_has_no_quantisation() -> None:
    body = "\n".join(source(c) for c in cells() if c["cell_type"] == "code")
    assert "bnb_4bit_compute_dtype=torch.float16" in body
    assert "fp16=(PRECISION == " in body
    assert "bf16=(PRECISION == " in body


def test_prep_helpers_mask_the_prompt_and_pad() -> None:
    prep = next(source(c) for c in cells() if "student-prep" in c["metadata"].get("tags", []))
    ns: dict = {}
    exec(prep, ns)

    class Tok:
        def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=False):
            text = "".join(f"<{m['role']}>{m['content']}" for m in msgs)
            return text + ("<assistant>" if add_generation_prompt else "")

        def __call__(self, text, add_special_tokens=False):
            return {"input_ids": [ord(ch) for ch in text]}

    row = {"messages": [{"role": "user", "content": "ab"}, {"role": "assistant", "content": "cd"}]}
    enc = ns["encode_row"](Tok(), row, 100)
    n_prompt = len("<user>ab<assistant>")
    assert enc is not None
    assert enc["labels"][:n_prompt] == [-100] * n_prompt
    assert enc["labels"][n_prompt:] == enc["input_ids"][n_prompt:]
    assert ns["encode_row"](Tok(), row, 5) is None  # too long
    ids, labels, mask = ns["collate"]([enc, {"input_ids": [1], "labels": [1]}], 0)
    assert len(ids[1]) == len(ids[0])
    assert labels[1][-1] == -100
    assert mask[1][-1] == 0
