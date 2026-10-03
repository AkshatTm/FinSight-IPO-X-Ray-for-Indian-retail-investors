"""Writes notebooks/b2_student_qlora_kaggle.ipynb (B2.5, the simplifier student, M6).

    uv run python scripts/make_student_notebook.py

QLoRA on a Kaggle T4 (fp16), checkpoints every 200 steps with resume, then merge and GGUF Q4_K_M
export with llama.cpp for the CPU worker. The training rows come from
``python -m finsight.risks.simplify split`` (chat format, the serving prompt as the user turn), so
the student is trained on exactly the prompt it is served with
(``tests/risks/test_student_notebook.py`` checks the committed file).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.risks import simplify  # noqa: E402

OUT = ROOT / "notebooks" / "b2_student_qlora_kaggle.ipynb"
DATASET = "finsight-simplify"

MD = """# B2.5 - Simplifier student: QLoRA on Kaggle + GGUF export (FinSight, M6)

Fine-tunes a small Qwen instruct model to rewrite risk factors in plain English, from the filtered
teacher pairs in the private dataset `finsight-simplify` (`train.jsonl`, `dev.jsonl`; split 95/5 by
company). **Runs on a Kaggle T4 (fp16)**; nothing trains on the laptop.

- QLoRA: 4-bit NF4 base, LoRA r=16, alpha=32, dropout 0.05 on the attention and MLP projections,
  lr 2e-4, max_seq 1,024, gradient checkpointing. Loss only on the answer tokens.
- Checkpoint every 200 steps to `/kaggle/working/student/checkpoints`; attach an earlier output and
  the run resumes from its last checkpoint.
- Then merge the adapter (fp16) and export **GGUF Q4_K_M** with llama.cpp for the Cloud Run CPU job.
- Outputs: `adapter/`, `merged/`, `simplifier-q4_k_m.gguf`, `metrics.json`.
- The teacher rewrites are AI-made; the student inherits the corpus's non-commercial terms.
  Keep the weights private (models/ and a private Hugging Face repo).
"""

PARAMS = """# ---- parameters ------------------------------------------------------------------------------
MODEL = "Qwen/Qwen3-4B-Instruct-2507"  # Apache-2.0, non-thinking; B2.5b bake-off may change it
DATASET = "finsight-simplify"
EPOCHS = 2
LEARNING_RATE = 2e-4
BATCH_SIZE = 2
GRAD_ACCUM = 8
MAX_SEQ = 1024
SAVE_STEPS = 200
SEED = 2026
SMOKE = False  # True: 64 train / 16 dev rows, 10 steps
EXPORT_GGUF = True
OUT_DIR = "/kaggle/working/student"
"""

SETUP = """import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "peft>=0.13", "bitsandbytes>=0.45"], check=True)
"""

PREP = """import json, math, random
from pathlib import Path

def read_rows(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def encode_row(tokenizer, row, max_seq):
    \"\"\"input_ids + labels with the prompt masked (-100); None when longer than max_seq.\"\"\"
    user, answer = row["messages"][0], row["messages"][1]["content"]
    prompt = tokenizer.apply_chat_template([user], tokenize=False, add_generation_prompt=True)
    full = tokenizer.apply_chat_template([user, {"role": "assistant", "content": answer}], tokenize=False)
    p_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    f_ids = tokenizer(full, add_special_tokens=False)["input_ids"]
    if len(f_ids) > max_seq or f_ids[: len(p_ids)] != p_ids:
        return None
    return {"input_ids": f_ids, "labels": [-100] * len(p_ids) + f_ids[len(p_ids):]}

def collate(batch, pad_id):
    n = max(len(b["input_ids"]) for b in batch)
    ids = [b["input_ids"] + [pad_id] * (n - len(b["input_ids"])) for b in batch]
    labels = [b["labels"] + [-100] * (n - len(b["labels"])) for b in batch]
    mask = [[1] * len(b["input_ids"]) + [0] * (n - len(b["input_ids"])) for b in batch]
    return ids, labels, mask
"""

BODY = """import shutil, time
import numpy as np
import torch
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer,
                          TrainingArguments)

ON_KAGGLE = Path("/kaggle/input").exists()
if ON_KAGGLE:
    DATA_DIR = next(p.parent for p in Path("/kaggle/input").rglob("train.jsonl"))
else:
    DATA_DIR, OUT_DIR = Path("data/processed/kaggle/simplify"), "student_out"
out = Path(OUT_DIR); out.mkdir(parents=True, exist_ok=True)
ckpt_dir = out / "checkpoints"
earlier = sorted(Path("/kaggle/input").rglob("checkpoint-*")) if ON_KAGGLE else []
if earlier and not ckpt_dir.exists():
    shutil.copytree(earlier[-1], ckpt_dir / earlier[-1].name)  # resume from the last checkpoint
    print("resuming from", earlier[-1])

train_rows, dev_rows = read_rows(DATA_DIR / "train.jsonl"), read_rows(DATA_DIR / "dev.jsonl")
assert not {r["company"] for r in train_rows} & {r["company"] for r in dev_rows}, "company on both sides"
if SMOKE:
    train_rows, dev_rows = train_rows[:64], dev_rows[:16]
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

tokenizer = AutoTokenizer.from_pretrained(MODEL)
pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
train = [e for e in (encode_row(tokenizer, r, MAX_SEQ) for r in train_rows) if e]
dev = [e for e in (encode_row(tokenizer, r, MAX_SEQ) for r in dev_rows) if e]
print(len(train), "train |", len(dev), "dev | skipped as too long:", len(train_rows) + len(dev_rows) - len(train) - len(dev))

class Rows(torch.utils.data.Dataset):
    def __init__(self, rows): self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, i): return self.rows[i]

def collator(batch):
    ids, labels, mask = collate(batch, pad_id)
    return {"input_ids": torch.tensor(ids), "labels": torch.tensor(labels), "attention_mask": torch.tensor(mask)}

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                         bnb_4bit_compute_dtype=torch.float16)  # T4: fp16, no bf16
model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=bnb, torch_dtype=torch.float16,
                                             device_map="auto")
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
model = get_peft_model(model, lora)
model.print_trainable_parameters()

args = TrainingArguments(
    output_dir=str(ckpt_dir), num_train_epochs=EPOCHS, max_steps=10 if SMOKE else -1,
    per_device_train_batch_size=BATCH_SIZE, per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM, learning_rate=LEARNING_RATE, lr_scheduler_type="cosine",
    warmup_ratio=0.03, fp16=True, gradient_checkpointing=True, logging_steps=10,
    eval_strategy="steps", eval_steps=SAVE_STEPS, save_strategy="steps", save_steps=SAVE_STEPS,
    save_total_limit=2, report_to="none", seed=SEED, remove_unused_columns=False)
trainer = Trainer(model=model, args=args, train_dataset=Rows(train), eval_dataset=Rows(dev), data_collator=collator)
t0 = time.time()
has_ckpt = any(ckpt_dir.glob("checkpoint-*"))
trainer.train(resume_from_checkpoint=True if has_ckpt else None)
eval_loss = trainer.evaluate()["eval_loss"]
model.save_pretrained(str(out / "adapter")); tokenizer.save_pretrained(str(out / "adapter"))
metrics = {"model": MODEL, "epochs": EPOCHS, "smoke": SMOKE, "n_train": len(train), "n_dev": len(dev),
           "dev_loss": eval_loss, "train_runtime_s": round(time.time() - t0),
           "log_history": trainer.state.log_history, "gpu": torch.cuda.get_device_name(0)}
del model, trainer; torch.cuda.empty_cache()

# ---- merge (fp16 on CPU RAM) -------------------------------------------------------------------
base = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="cpu")
merged = PeftModel.from_pretrained(base, str(out / "adapter")).merge_and_unload()
merged.save_pretrained(str(out / "merged"), safe_serialization=True); tokenizer.save_pretrained(str(out / "merged"))
del base, merged

# ---- GGUF Q4_K_M ---------------------------------------------------------------------------------
if EXPORT_GGUF:
    run = lambda cmd: subprocess.run(cmd, check=True, shell=True)
    lc = Path("/tmp/llama.cpp")  # outside /kaggle/working, so it is not saved as output
    if not lc.exists():
        run(f"git clone --depth 1 https://github.com/ggml-org/llama.cpp {lc}")
    run(f"{sys.executable} -m pip install -q -r {lc}/requirements/requirements-convert_hf_to_gguf.txt")
    run(f"{sys.executable} {lc}/convert_hf_to_gguf.py {out / 'merged'} --outtype f16 --outfile {out / 'f16.gguf'}")
    run(f"cmake -S {lc} -B {lc}/build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF && cmake --build {lc}/build --target llama-quantize -j 4")
    run(f"{lc}/build/bin/llama-quantize {out / 'f16.gguf'} {out / 'simplifier-q4_k_m.gguf'} Q4_K_M")
    (out / "f16.gguf").unlink()
    metrics["gguf_mb"] = round((out / "simplifier-q4_k_m.gguf").stat().st_size / 2**20)
(out / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
print("STUDENT OK", json.dumps({k: v for k, v in metrics.items() if k != "log_history"}))
"""


def _cell(kind: str, src: str, tags: list[str] | None = None) -> dict[str, Any]:
    cell: dict[str, Any] = {
        "cell_type": kind,
        "metadata": {"tags": tags} if tags else {},
        "source": src.splitlines(keepends=True),
    }
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    return cell


def prompt_cell() -> str:
    """The serving prompt as literals (documentation in the notebook; the rows already use it)."""
    return (
        "# GENERATED from finsight.risks.simplify by scripts/make_student_notebook.py; do not edit\n"
        f"PROMPT_VERSION = {simplify.PROMPT_VERSION!r}\n"
        f"INSTRUCTIONS = {simplify.INSTRUCTIONS!r}\n"
        f"MAX_NEW_TOKENS = {simplify.MAX_NEW_TOKENS!r}\n"
    )


def build() -> dict[str, Any]:
    return {
        "cells": [
            _cell("markdown", MD),
            _cell("code", PARAMS, ["parameters"]),
            _cell("code", SETUP),
            _cell("code", prompt_cell(), ["student-prompt"]),
            _cell("code", PREP, ["student-prep"]),
            _cell("code", BODY),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
