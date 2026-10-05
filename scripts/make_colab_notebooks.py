"""Writes the Colab notebooks under ``notebooks/colab/`` (C0.2 onward).

    uv run python scripts/make_colab_notebooks.py            # (re)write all
    uv run python scripts/make_colab_notebooks.py --check    # fail when a notebook is stale

Notebooks are generated from this file so cells stay reviewable and testable. Later parts
(C2.2, C2.3, C2.5) add their builders to ``BUILDERS``. Each notebook starts with a parameter
cell, pins its libraries, checkpoints through ``_common`` and ends with ``run_summary``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "colab"


def cell(kind: str, src: str, tags: list[str] | None = None) -> dict[str, Any]:
    """One notebook cell (markdown or code)."""
    meta: dict[str, Any] = {"tags": tags} if tags else {}
    base: dict[str, Any] = {
        "cell_type": kind,
        "metadata": meta,
        "source": src.strip("\n").splitlines(keepends=True),
    }
    if kind == "code":
        base.update(execution_count=None, outputs=[])
    return base


def notebook(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap cells as an nbformat-4 notebook with a GPU Colab runtime."""
    for i, c in enumerate(cells):
        c["id"] = str(i)  # nbformat 5 wants cell ids; same form as nbstripout writes
    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


COMMON_CELL = """
# Shared helpers: copy notebooks/colab/_common.py to MyDrive/FinSight/_common.py once (COLAB_STEPS).
import sys, time
sys.path.insert(0, "/content/drive/MyDrive/FinSight")
from google.colab import drive
drive.mount("/content/drive")
from _common import mount_drive, Checkpointer, run_summary, gpu_info, unassign_runtime
STARTED = time.time()
JOB_DIR = mount_drive("rate_check")
print(gpu_info())
"""


def rate_check() -> dict[str, Any]:
    """C0.2 smoke notebook: GPU info, matmul timing, vLLM pin test with a small AWQ model."""
    md = """# C0.2 — Colab rate check + vLLM smoke (FinSight)

Run once per GPU. **T4 and A100: rate check only** (set `RUN_VLLM = False`). **L4: also the vLLM
test** (`RUN_VLLM = True`): `awq_marlin` needs compute capability 8.0+, so it cannot run on a T4.
Read the compute units in the Colab Resources panel before and after the run and type them in the
parameter cell. Keep the run about 10 minutes. Steps: `docs/phase3/COLAB_STEPS_rate_check.md`.
"""
    params = """
# ---- parameters (edit, then Run all) ------------------------------------------------------
UNITS_BEFORE = None      # compute units shown in the Resources panel before the run
UNITS_AFTER = None       # ... and after the run (type it before running the last cell)
RUN_VLLM = False         # True on the L4 only
MODEL = "Qwen/Qwen3-4B-AWQ"   # small AWQ model for the smoke test
# candidate vLLM pins, tried in order; the first that imports and generates becomes THE pin
VLLM_CANDIDATES = ["vllm==0.11.0", "vllm==0.10.2", "vllm"]
MATMUL_SECONDS = 120
UNASSIGN = False         # True disconnects the runtime when the last cell ends
"""
    matmul = """
import torch
assert torch.cuda.is_available(), "Runtime > Change runtime type > pick a GPU"
n, t0, iters = 4096, time.time(), 0
a = torch.randn(n, n, device="cuda", dtype=torch.float16); b = torch.randn(n, n, device="cuda", dtype=torch.float16)
while time.time() - t0 < MATMUL_SECONDS:
    for _ in range(50):
        a @ b
    torch.cuda.synchronize(); iters += 50
tflops = round(2 * n**3 * iters / (time.time() - t0) / 1e12, 2)
cap = torch.cuda.get_device_capability()
print({"fp16_tflops": tflops, "capability": cap, "torch": torch.__version__})
EXTRA = {"fp16_tflops": tflops, "capability": list(cap), "torch": torch.__version__}
"""
    vllm = '''
import subprocess, json
PIN_OK = None
if RUN_VLLM and cap[0] >= 8:
    for pin in VLLM_CANDIDATES:
        print("trying", pin)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pin], check=False)
        test = f"""
from vllm import LLM, SamplingParams
llm = LLM('{MODEL}', quantization='awq_marlin', max_model_len=2048, gpu_memory_utilization=0.85)
out = llm.generate(['Explain an IPO in one sentence.'], SamplingParams(max_tokens=40))
print('GEN_OK', out[0].outputs[0].text)
"""
        r = subprocess.run([sys.executable, "-c", test], capture_output=True, text=True)
        print(r.stdout[-800:], r.stderr[-800:])
        if "GEN_OK" in r.stdout:
            PIN_OK = pin
            break
    ver = subprocess.run([sys.executable, "-m", "pip", "show", "vllm"], capture_output=True, text=True).stdout
    EXTRA.update(vllm_pin=PIN_OK, vllm_pip_show=ver[:300], model=MODEL, quantization="awq_marlin")
else:
    print("vLLM test skipped (RUN_VLLM False or GPU below sm80)")
'''
    summary = """
s = run_summary(JOB_DIR, "rate_check", started=STARTED, units_before=UNITS_BEFORE,
                units_after=UNITS_AFTER, items_done=0, pins={"vllm": str(PIN_OK)}, extra=EXTRA)
print(json.dumps(s, indent=1))
print("Copy run_summary.json from Drive to eval_results/c/ and run scripts/log_compute.py on it.")
unassign_runtime(UNASSIGN)
"""
    return notebook(
        [
            cell("markdown", md),
            cell("code", params, ["parameters"]),
            cell("code", COMMON_CELL),
            cell("code", matmul),
            cell("code", vllm),
            cell("code", summary),
        ]
    )


TEACHER_PARAMS = """
# ---- parameters (edit, then Run all) ------------------------------------------------------
JOB = "teacher_bakeoff"            # Drive folder MyDrive/FinSight/<JOB>/ ; "teacher_full" for the real run
INPUT_FILE = "bakeoff_risks.jsonl" # in that folder: risk_id, title, body (risks.jsonl for the full run)
MODELS = ["Qwen/Qwen3-14B-AWQ", "Qwen/Qwen3-32B-AWQ"]   # full run: only the chosen model
SMOKE = True                       # True: 20 risks per model, then stop (run on a T4/L4 first)
EVERY = 100                        # checkpoint interval (risks per vLLM batch); 200 for the full run
MAX_MODEL_LEN = 4096
MAX_TOKENS = 400
VLLM_PIN = "vllm==0.11.0"          # REPLACE with the pin recorded by the L4 rate check (COLAB_STEPS_rate_check)
QUANT = "awq_marlin"               # awq_marlin needs sm80+ (L4/A100); a T4 needs "awq"
GPU_MEM = 0.90
MIN_GB_FOR_32B = 40                # the 32B model is skipped on a smaller GPU (L4-only fallback, C03 section 3)
UNITS_BEFORE = None                # compute units in the Resources panel before the run
UNITS_AFTER = None                 # ... and after (type it, then re-run the last cell)
UNASSIGN = False                   # True disconnects the runtime at the end
"""

TEACHER_INSTALL = """
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", VLLM_PIN], check=True)
"""

TEACHER_BODY = """
import gc, json, os, time
from pathlib import Path
import torch
from vllm import LLM, SamplingParams

JOB_DIR = mount_drive(JOB)
LIMIT = 20 if SMOKE else None
gpu_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
risks = list(read_jsonl(JOB_DIR / INPUT_FILE))
items = [{"risk_id": r["risk_id"], "messages": messages(r.get("title") or "", r["body"])} for r in risks]
print(len(items), "risks; GPU", gpu_info(), f"{gpu_gb:.0f} GB")
ck = Checkpointer(local_dir="/content/ck", drive_dir=JOB_DIR / "out", every=1)
PINS = {"vllm": VLLM_PIN, "torch": torch.__version__}
for model in MODELS:
    slug = model.split("/")[-1].lower()
    if "32b" in slug and gpu_gb < MIN_GB_FOR_32B:
        print("skipping", model, "- GPU too small; use the 14B model directly (C-ADR-05 fallback)")
        continue
    out_path = ck.path(f"raw_{slug}.jsonl")
    llm = LLM(model=model, quantization=QUANT, dtype="float16", max_model_len=MAX_MODEL_LEN,
              gpu_memory_utilization=GPU_MEM, enforce_eager=False, seed=2026)
    try:  # vLLM <= 0.10
        from vllm.sampling_params import GuidedDecodingParams
        params = SamplingParams(temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS,
                                guided_decoding=GuidedDecodingParams(json=OUTPUT_SCHEMA))
    except ImportError:  # newer releases renamed it
        from vllm.sampling_params import StructuredOutputsParams
        params = SamplingParams(temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS,
                                structured_outputs=StructuredOutputsParams(json=OUTPUT_SCHEMA))

    def generate(chats):
        outs = llm.chat(chats, params, use_tqdm=False, chat_template_kwargs={"enable_thinking": False})
        return [o.outputs[0].text for o in outs]

    t0 = time.time()
    stats = run_teacher(items, generate, out_path, every=EVERY, limit=LIMIT,
                        meta={"model": model, "prompt_version": PROMPT_VERSION}, after_batch=ck.sync)
    seconds = round(time.time() - t0)
    ck.sync()
    summary = {**stats, "model": model, "prompt_version": PROMPT_VERSION, "seconds": seconds,
               "smoke": SMOKE, "gpu": gpu_info(), "pins": PINS}
    ck.path(f"run_summary_{slug}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    ck.sync()
    print("TEACHER OK", json.dumps(summary))
    del llm
    gc.collect()
    torch.cuda.empty_cache()
"""

TEACHER_END = """
s = run_summary(JOB_DIR, JOB, started=STARTED, units_before=UNITS_BEFORE, units_after=UNITS_AFTER,
                items_done=len(items), pins=PINS, extra={"models": MODELS, "smoke": SMOKE})
print(json.dumps(s, indent=1))
print("Copy raw_*.jsonl, run_summary_*.json (folder out/) and run_summary.json back (COLAB_STEPS).")
unassign_runtime(UNASSIGN)
"""


def teacher() -> dict[str, Any]:
    """C2.2 / C2.3: the teacher notebook (bake-off with two models, or the full run with one)."""
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_teacher_notebook as legacy

    md = """# C2.2 / C2.3 - Teacher labels and plain-English rewrites (FinSight, Colab)

Runs Qwen3 AWQ teachers with **vLLM** over a risks file (`risk_id`, `title`, `body`). Inference
only. One JSON answer per risk: `category`, `seriousness_1to5`, `hard_fact`, `simple`
(<= 60 words), `numbers_copied`. Thinking mode is off. The prompt and the loop are copied from
`finsight.risks` by `scripts/make_colab_notebooks.py`, so they are the tested ones.

- **Bake-off (C2.2):** `JOB = "teacher_bakeoff"`, both models, A100 (the 32B model needs ~40 GB).
- **Full run (C2.3):** `JOB = "teacher_full"`, one model, `EVERY = 200`.
- **Smoke first** (`SMOKE = True`, 20 risks) on a T4 or L4 with the small model; then `SMOKE = False`.
- Answers are appended to local disk and copied to Drive after every batch; a disconnect resumes.
- Filters run on the laptop, not here. Teacher outputs are AI labels (`label_source`).
"""
    cells = [
        cell("markdown", md),
        cell("code", TEACHER_PARAMS, ["parameters"]),
        cell("code", TEACHER_INSTALL),
        cell("code", COMMON_CELL.replace('JOB_DIR = mount_drive("rate_check")\n', "")),
        cell("code", legacy.RUN_SOURCE.read_text(encoding="utf-8"), ["teacher-run"]),
        cell("code", "import json\n\n" + legacy.prompt_cell(), ["teacher-prompt"]),
        cell("code", TEACHER_BODY),
        cell("code", TEACHER_END),
    ]
    return notebook(cells)


STUDENT_PARAMS = """
# ---- parameters (edit, then Run all) ------------------------------------------------------
JOB = "student"                    # Drive folder MyDrive/FinSight/student/ holds train.jsonl and dev.jsonl
MODEL = "Qwen/Qwen3-4B-Instruct-2507"   # Apache-2.0, non-thinking; the zero-shot bake-off may change it
PRECISION = "bf16"                 # "bf16": LoRA on a bf16 base (L4/A100); "nf4": 4-bit QLoRA, the T4 recipe
EPOCHS = 2
LEARNING_RATE = 2e-4
BATCH_SIZE = 2                     # raise to 8 on an A100 in bf16
GRAD_ACCUM = 8
MAX_SEQ = 1024
SAVE_STEPS = 200
SEED = 2026
SMOKE = True                       # True: 64 train / 16 dev rows, 10 steps (run on a T4 with PRECISION = "nf4")
EXPORT_GGUF = True
UPLOAD = False                     # True: push adapter + GGUF (never merged fp16) to a private HF repo
HF_REPO = "AkshatTm/finsight-student-4b"
UNITS_BEFORE = None
UNITS_AFTER = None
UNASSIGN = False
"""

STUDENT_SETUP = """
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "peft>=0.13", "bitsandbytes>=0.45",
                "huggingface_hub"], check=True)
"""

STUDENT_BODY = """
import json, random, shutil, time
from pathlib import Path
import numpy as np
import torch
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer,
                          TrainerCallback, TrainingArguments)

assert PRECISION in ("bf16", "nf4"), PRECISION
JOB_DIR = mount_drive(JOB)
out = Path("/content/student")
out.mkdir(parents=True, exist_ok=True)
ck = Checkpointer(local_dir=out / "ck", drive_dir=JOB_DIR / "ck", every=10**9)  # synced on every save
ckpt_dir = ck.local / "trainer"

train_rows, dev_rows = read_rows(JOB_DIR / "train.jsonl"), read_rows(JOB_DIR / "dev.jsonl")
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

if PRECISION == "nf4":  # the T4 recipe: 4-bit base, fp16 compute
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                             bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=bnb, torch_dtype=torch.float16,
                                                 device_map="auto")
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
else:  # L4/A100: LoRA on a bf16 base, no quantisation
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16, device_map="auto")
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
model = get_peft_model(model, lora)
model.print_trainable_parameters()

class SyncToDrive(TrainerCallback):
    def on_save(self, args, state, control, **kwargs):
        ck.sync()  # a disconnect loses at most SAVE_STEPS steps

args = TrainingArguments(
    output_dir=str(ckpt_dir), num_train_epochs=EPOCHS, max_steps=10 if SMOKE else -1,
    per_device_train_batch_size=BATCH_SIZE, per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM, learning_rate=LEARNING_RATE, lr_scheduler_type="cosine",
    warmup_ratio=0.03, fp16=(PRECISION == "nf4"), bf16=(PRECISION == "bf16"), gradient_checkpointing=True,
    logging_steps=10, eval_strategy="steps", eval_steps=SAVE_STEPS, save_strategy="steps",
    save_steps=SAVE_STEPS, save_total_limit=2, report_to="none", seed=SEED, remove_unused_columns=False)
trainer = Trainer(model=model, args=args, train_dataset=Rows(train), eval_dataset=Rows(dev),
                  data_collator=collator, callbacks=[SyncToDrive()])
t0 = time.time()
resume = ck.latest_trainer_checkpoint("trainer")
print("resuming from", resume) if resume else print("fresh run")
trainer.train(resume_from_checkpoint=resume)
eval_loss = trainer.evaluate()["eval_loss"]
adapter = out / "adapter"
model.save_pretrained(str(adapter)); tokenizer.save_pretrained(str(adapter))
metrics = {"model": MODEL, "precision": PRECISION, "epochs": EPOCHS, "smoke": SMOKE, "n_train": len(train),
           "n_dev": len(dev), "dev_loss": eval_loss, "train_runtime_s": round(time.time() - t0),
           "log_history": trainer.state.log_history, "gpu": torch.cuda.get_device_name(0)}
del model, trainer; torch.cuda.empty_cache()

# ---- merge (temporary, only to make the GGUF; the merged fp16 weights are deleted below) --------
gguf = out / "simplifier-q4_k_m.gguf"
if EXPORT_GGUF:
    base = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="cpu")
    merged = PeftModel.from_pretrained(base, str(adapter)).merge_and_unload()
    merged.save_pretrained(str(out / "merged"), safe_serialization=True); tokenizer.save_pretrained(str(out / "merged"))
    del base, merged
    run = lambda cmd: subprocess.run(cmd, check=True, shell=True)
    lc = Path("/tmp/llama.cpp")
    if not lc.exists():
        run(f"git clone --depth 1 https://github.com/ggml-org/llama.cpp {lc}")
    run(f"{sys.executable} -m pip install -q -r {lc}/requirements/requirements-convert_hf_to_gguf.txt")
    run(f"{sys.executable} {lc}/convert_hf_to_gguf.py {out / 'merged'} --outtype f16 --outfile {out / 'f16.gguf'}")
    run(f"cmake -S {lc} -B {lc}/build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF && cmake --build {lc}/build --target llama-quantize -j 4")
    run(f"{lc}/build/bin/llama-quantize {out / 'f16.gguf'} {gguf} Q4_K_M")
    (out / "f16.gguf").unlink()
    shutil.rmtree(out / "merged")  # never kept: merged fp16 weights do not go to Drive or the Hub
    metrics["gguf_mb"] = round(gguf.stat().st_size / 2**20)
(out / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")

# ---- keep the small files on Drive; optionally upload to a private HF repo --------------------------
keep = JOB_DIR / "out"
keep.mkdir(parents=True, exist_ok=True)
shutil.copytree(adapter, keep / "adapter", dirs_exist_ok=True)
shutil.copy(out / "metrics.json", keep / "metrics.json")
if EXPORT_GGUF:
    shutil.copy(gguf, keep / gguf.name)
if UPLOAD:
    from google.colab import userdata
    from huggingface_hub import HfApi
    api = HfApi(token=userdata.get("HF_TOKEN"))
    api.create_repo(HF_REPO, private=True, exist_ok=True)
    api.upload_folder(folder_path=str(adapter), path_in_repo="adapter", repo_id=HF_REPO)
    if EXPORT_GGUF:
        api.upload_file(path_or_fileobj=str(gguf), path_in_repo=gguf.name, repo_id=HF_REPO)
    print("uploaded adapter + GGUF to the private repo", HF_REPO)
print("STUDENT OK", json.dumps({k: v for k, v in metrics.items() if k != "log_history"}))
"""

STUDENT_END = """
s = run_summary(JOB_DIR, "student", started=STARTED, units_before=UNITS_BEFORE, units_after=UNITS_AFTER,
                items_done=len(train), pins={"torch": torch.__version__}, extra={"precision": PRECISION, "smoke": SMOKE})
print(json.dumps(s, indent=1))
unassign_runtime(UNASSIGN)
"""


def student() -> dict[str, Any]:
    """C2.5: the student simplifier (LoRA on a 4B model, GGUF export) on Colab."""
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_student_notebook as legacy

    md = """# C2.5 - Simplifier student: LoRA on Colab + GGUF export (FinSight, M6)

Fine-tunes a ~4B Qwen instruct model to rewrite risk factors in plain English, from the filtered
teacher pairs (`train.jsonl`, `dev.jsonl` in `MyDrive/FinSight/student/`, made by
`python -m finsight.risks.simplify split`; split by company). The training rows already use the
serving prompt (`finsight.risks.simplify`).

- **PRECISION `bf16`** (L4/A100): LoRA r=16 on a bf16 base, no 4-bit. **`nf4`**: the T4 recipe (4-bit, fp16).
- Checkpoints go to local disk and are copied to Drive on every save (`SAVE_STEPS`); a disconnect resumes.
- Then the adapter is merged **temporarily** to make a **GGUF Q4_K_M** with llama.cpp. The merged fp16
  weights are deleted. Only the adapter and the GGUF are kept (Drive) and, with `UPLOAD`, pushed to a
  **private** Hugging Face repo. Never merged fp16.
- The teacher rewrites are AI-made, and the corpus terms are non-commercial: keep the repo private.
- Smoke first (`SMOKE = True`, T4, `nf4`), then the real run on an L4 or A100.
"""
    cells = [
        cell("markdown", md),
        cell("code", STUDENT_PARAMS, ["parameters"]),
        cell("code", STUDENT_SETUP),
        cell("code", COMMON_CELL.replace('JOB_DIR = mount_drive("rate_check")\n', "")),
        cell("code", legacy.prompt_cell(), ["student-prompt"]),
        cell("code", legacy.PREP, ["student-prep"]),
        cell("code", STUDENT_BODY),
        cell("code", STUDENT_END),
    ]
    return notebook(cells)


BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "c0_rate_check.ipynb": rate_check,
    "c2_teacher.ipynb": teacher,
    "c2_student.ipynb": student,
}


def render(nb: dict[str, Any]) -> str:
    """Stable JSON text (LF, 1-space indent like Jupyter)."""
    return json.dumps(nb, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write or check all notebooks."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    stale = []
    for name, build in BUILDERS.items():
        text, path = render(build()), OUT / name
        if a.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            print("wrote", path.relative_to(ROOT))
    if stale:
        print("stale notebooks:", stale)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
