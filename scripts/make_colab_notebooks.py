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


JOBS_REPO = "AkshatTm/finsight-gpu-jobs"  # private HF dataset repo (scripts/gpu_jobs.py)

# Cell 1 of every notebook: where inputs and checkpoints live. Defaults to the private HF repo
# (a fresh runtime resumes from it); "drive" is the fallback and needs _common.py on Drive.
COMMON_CELL = """
# Shared helpers. IO "hf": _common.py comes from the job repo (pushed by scripts/gpu_jobs.py);
# IO "drive": copy notebooks/colab/_common.py to MyDrive/FinSight/ once. Secrets are never printed.
import os, sys, time
STARTED = time.time()
if IO == "hf":
    from huggingface_hub import hf_hub_download
    from google.colab import userdata
    _tok = userdata.get("HF_TOKEN")   # Colab secret: enable "Notebook access" for HF_TOKEN
    hf_hub_download(JOBS_REPO, "_common.py", repo_type="dataset", token=_tok,
                    local_dir="/content/_boot", force_download=True)
    sys.path.insert(0, "/content/_boot")
else:
    from google.colab import drive
    drive.mount("/content/drive")
    sys.path.insert(0, "/content/drive/MyDrive/FinSight")
from _common import (JobIO, Checkpointer, DirBackend, run_summary, gpu_info, gpu_config,
                     gpu_probe, gpu_tier, hf_secret, unassign_runtime)
print(gpu_info())
"""

RATE_PRESETS = """
PRESETS = {
    # GPU speed + vLLM pin test (the vLLM test runs when the GPU is sm80+: L4, A100, H100)
    "rate_check": {"job": "rate_check", "run_vllm": True, "matmul_seconds": 120,
                   "model": "Qwen/Qwen3-4B-AWQ"},
    # speed only, any GPU including a T4
    "rate_only": {"job": "rate_check", "run_vllm": False, "matmul_seconds": 120,
                  "model": "Qwen/Qwen3-4B-AWQ"},
}
"""


def rate_check() -> dict[str, Any]:
    """C0.2 smoke notebook: GPU info, matmul timing, vLLM pin test with a small AWQ model."""
    md = """# C0.2 — Colab rate check + vLLM smoke (FinSight)

Pick `PRESET`, then **Run all**. `rate_check` also runs the vLLM pin test (needs sm80+: L4,
A100, H100; a T4 skips it). The kernel and memory settings come from the detected GPU. Inputs and
outputs go through the private HF repo (`IO = "hf"`). `UNITS_BEFORE` from the Resources panel;
`UNITS_AFTER` may stay empty (give it to `scripts/gpu_jobs.py pull`). The runtime disconnects
itself at the end (`UNASSIGN`). Steps: `docs/phase3/COLAB_STEPS_rate_check.md`.
"""
    params = (
        """
# ---- parameters: pick a preset, then Run all ------------------------------------------------
PRESET = "rate_check"          # rate_check | rate_only
IO = "hf"                      # "hf" (private job repo, default) | "drive" (fallback)
JOBS_REPO = "AkshatTm/finsight-gpu-jobs"
UNITS_BEFORE = None            # compute units in the Resources panel before the run
UNITS_AFTER = None             # optional; gpu_jobs.py pull --units-after fills it in later
UNASSIGN = True                # disconnect the runtime when the job ends
# candidate vLLM pins, tried in order; the first that imports and generates becomes THE pin
VLLM_CANDIDATES = ["vllm==0.31.0", "vllm==0.30.0", "vllm==0.29.0"]
"""
        + RATE_PRESETS
        + """
_P = PRESETS[PRESET]
JOB, RUN_VLLM, MATMUL_SECONDS, MODEL = _P["job"], _P["run_vllm"], _P["matmul_seconds"], _P["model"]
"""
    )
    matmul = """
import torch
assert torch.cuda.is_available(), "Runtime > Change runtime type > pick a GPU"
CFG = gpu_config(torch.cuda.get_device_name(0),
                 torch.cuda.get_device_properties(0).total_memory / 1024**3,
                 torch.cuda.get_device_capability())
print("GPU config:", CFG)
n, t0, iters = 4096, time.time(), 0
a = torch.randn(n, n, device="cuda", dtype=torch.float16); b = torch.randn(n, n, device="cuda", dtype=torch.float16)
while time.time() - t0 < MATMUL_SECONDS:
    for _ in range(50):
        a @ b
    torch.cuda.synchronize(); iters += 50
tflops = round(2 * n**3 * iters / (time.time() - t0) / 1e12, 2)
cap = torch.cuda.get_device_capability()
print({"fp16_tflops": tflops, "capability": cap, "torch": torch.__version__})
EXTRA = {"fp16_tflops": tflops, "capability": list(cap), "torch": torch.__version__, "gpu_config": CFG,
         "preset": PRESET}
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
llm = LLM('{MODEL}', quantization='{CFG["quant"]}', max_model_len=2048, gpu_memory_utilization={CFG["gpu_mem"]})
out = llm.generate(['Explain an IPO in one sentence.'], SamplingParams(max_tokens=40))
print('GEN_OK', out[0].outputs[0].text)
import time
ps = ['Rewrite this risk in plain English, keep every number: risk ' + str(i) for i in range(128)]
t = time.time()
outs = llm.generate(ps, SamplingParams(max_tokens=256, temperature=0, ignore_eos=True))
print('TOKS_PER_S', round(sum(len(o.outputs[0].token_ids) for o in outs) / (time.time() - t), 1))
"""
        r = subprocess.run([sys.executable, "-c", test], capture_output=True, text=True)
        print(r.stdout[-800:], r.stderr[-800:])
        if "GEN_OK" in r.stdout:
            PIN_OK = pin
            m = [ln for ln in r.stdout.splitlines() if ln.startswith("TOKS_PER_S")]
            EXTRA["decode_toks_per_s_128x256"] = float(m[-1].split()[1]) if m else None
            break
    ver = subprocess.run([sys.executable, "-m", "pip", "show", "vllm"], capture_output=True, text=True).stdout
    EXTRA.update(vllm_pin=PIN_OK, vllm_pip_show=ver[:300], model=MODEL, quantization=CFG["quant"])
else:
    print("vLLM test skipped (RUN_VLLM False or GPU below sm80)")
'''
    summary = """
try:
    JOBIO = JobIO(JOB, IO, hf_repo=JOBS_REPO, token=hf_secret())
    ck = JOBIO.checkpointer(every=1)
    s = run_summary(ck.local, "rate_check", started=STARTED, units_before=UNITS_BEFORE,
                    units_after=UNITS_AFTER, items_done=0, pins={"vllm": str(PIN_OK)}, extra=EXTRA)
    ck.sync()
    print(json.dumps(s, indent=1))
    print("RATE CHECK DONE. vllm_pin =", PIN_OK)
finally:
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


TEACHER_PRESETS = """
# candidate teachers (C2.2, C-ADR-05 as accepted); the full run uses only the chosen one
QWEN38 = "Qwen/Qwen3.8-27B-FP8"     # Apache-2.0, FP8 checkpoint (native on the G4)
GEMMA4 = "google/gemma-4-31B-it"    # Apache-2.0, bf16 (~63 GB)
BASELINE = "Qwen/Qwen3-32B-AWQ"     # Apache-2.0, AWQ 4-bit
CANDIDATES = [QWEN38, GEMMA4, BASELINE]
TEACHER = TEACHER_PICK or BASELINE  # set TEACHER_PICK above once the bake-off is scored
PRESETS = {
    # 20 risks per model, then stop: must print TEACHER OK. Models too big for the GPU are skipped.
    "bakeoff_smoke": {"job": "bakeoff", "input": "bakeoff_risks.jsonl", "models": CANDIDATES,
                      "smoke": True, "every": 20, "max_tokens": 300},
    "bakeoff": {"job": "bakeoff", "input": "bakeoff_risks.jsonl", "models": CANDIDATES,
                "smoke": False, "every": 50, "max_tokens": 300},
    "teacher_smoke": {"job": "teacher_full", "input": "risks.jsonl", "models": [TEACHER],
                      "smoke": True, "every": 20, "max_tokens": 300},
    "teacher_full": {"job": "teacher_full", "input": "risks.jsonl", "models": [TEACHER],
                     "smoke": False, "every": 200, "max_tokens": 300},
    # test-slice gold sets (C2.4 gold-150 pre-fill, C2.5 gold-50 teacher system): evaluation only
    "gold_eval": {"job": "gold_eval", "input": "gold_eval_risks.jsonl", "models": [TEACHER, QWEN38],
                  "smoke": False, "every": 50, "max_tokens": 300},
}
"""

TEACHER_PARAMS = (
    """
# ---- parameters: pick a preset, then Run all ------------------------------------------------
PRESET = "bakeoff_smoke"   # bakeoff_smoke | bakeoff | teacher_smoke | teacher_full | gold_eval
IO = "hf"                  # "hf" (private job repo, default) | "drive" (fallback)
JOBS_REPO = "AkshatTm/finsight-gpu-jobs"
UNITS_BEFORE = None        # compute units in the Resources panel before the run
UNITS_AFTER = None         # optional; gpu_jobs.py pull --units-after fills it in later
UNASSIGN = True            # disconnect the runtime when the job ends (also if it crashes)
VLLM_PIN = "vllm==0.31.0"  # C0.2 pin: works on L4 (sm89) and G4 RTX PRO 6000 Blackwell (sm120)
MODELS_OVERRIDE = None     # e.g. ["org/model-AWQ"]; None = the preset's models
QUANT_OVERRIDE = None      # None = AWQ repos: kernel from the GPU; FP8/compressed-tensors/NVFP4: from the checkpoint
MAX_MODEL_LEN = 4096
TEACHER_PICK = "google/gemma-4-31B-it"  # C-ADR-05 winner (eval_results/c/teacher_bakeoff.json)
"""
    + TEACHER_PRESETS
    + """
_P = PRESETS[PRESET]
JOB, INPUT_FILE, SMOKE, EVERY, MAX_TOKENS = _P["job"], _P["input"], _P["smoke"], _P["every"], _P["max_tokens"]
MODELS = MODELS_OVERRIDE or _P["models"]
assert JOB != "teacher_full" or TEACHER_PICK or MODELS_OVERRIDE, "set TEACHER_PICK (the C-ADR-05 winner) first"
"""
)

TEACHER_INSTALL = """
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", VLLM_PIN], check=True)
"""

# The body is a function so the whole run sits in try/finally: the GPU is released even on a crash.
TEACHER_MAIN = """
import gc, json, os, re, time
from pathlib import Path
import torch
from vllm import LLM, SamplingParams


def model_fits(model, gpu_gb, gpu_mem):
    # GiB per billion parameters: 4-bit ~0.6, FP8 ~1.1, bf16 ~2.0; plus ~4 GiB for CUDA and KV cache
    name = model.split("/")[-1].lower()
    m = re.search(r"(\\d+(?:\\.\\d+)?)b", name)
    four_bit = any(t in name for t in ("awq", "gptq", "w4a16", "nvfp4", "mxfp4", "int4", "4bit"))
    per_b = 0.6 if four_bit else 1.1 if "fp8" in name else 2.0
    return True if m is None else gpu_gb * gpu_mem >= per_b * float(m.group(1)) + 4


def load_kwargs(model, gpu_quant):
    # AWQ repos take the GPU's AWQ kernel and fp16; other checkpoints declare their own quantisation
    awq = "awq" in model.lower()
    kw = {"quantization": QUANT_OVERRIDE or (gpu_quant if awq else None), "dtype": "float16" if awq else "auto"}
    try:
        from transformers import AutoConfig
        vision = getattr(AutoConfig.from_pretrained(model), "vision_config", None) is not None
    except Exception:  # unknown config: load as is (a VLM then also loads its vision encoder)
        vision = False
    if vision:
        kw["limit_mm_per_prompt"] = {"image": 0, "video": 0}  # vision-language model: text only
    return kw


def main():
    LIMIT = 20 if SMOKE else None
    # no torch.cuda call before vLLM: CUDA in this process would force vLLM's engine onto "spawn"
    probe = gpu_probe()
    assert probe, "no GPU: Runtime > Change runtime type"
    gpu_name, gpu_gb, gpu_cap = probe
    CFG = gpu_config(gpu_name, gpu_gb, gpu_cap)
    quant = QUANT_OVERRIDE or CFG["quant"]
    print(f"PRESET {PRESET} | GPU {CFG['tier']} {CFG['mem_gb']} GiB | quant {quant} | models {MODELS}", flush=True)
    jobio = JobIO(JOB, IO, hf_repo=JOBS_REPO, token=hf_secret())
    ck = jobio.checkpointer(every=1)  # every batch is synced to the HF repo / Drive
    risks = list(read_jsonl(jobio.fetch_input(INPUT_FILE)))
    items = [{"risk_id": r["risk_id"], "messages": messages(r.get("title") or "", r["body"])} for r in risks]
    total = min(len(items), LIMIT) if LIMIT else len(items)
    print(len(items), "risks;", "will write", total, "per model", flush=True)
    pins = {"vllm": VLLM_PIN, "torch": torch.__version__}
    written = 0
    for model in MODELS:
        slug = model.split("/")[-1].lower()
        if not model_fits(model, gpu_gb, CFG["gpu_mem"]):
            print("skipping", model, f"- does not fit {gpu_gb:.0f} GiB (use a larger GPU or the smaller model)", flush=True)
            continue
        out_path = ck.path(f"raw_{slug}.jsonl")
        kw = load_kwargs(model, quant)
        if CFG.get("max_num_seqs"):
            kw["max_num_seqs"] = CFG["max_num_seqs"]
        llm = LLM(model=model, max_model_len=MAX_MODEL_LEN, gpu_memory_utilization=CFG["gpu_mem"],
                  enforce_eager=False, seed=2026, **kw)
        try:  # vLLM <= 0.10
            from vllm.sampling_params import GuidedDecodingParams
            params = SamplingParams(temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS,
                                    guided_decoding=GuidedDecodingParams(json=OUTPUT_SCHEMA))
        except ImportError:  # newer releases renamed it
            from vllm.sampling_params import StructuredOutputsParams
            params = SamplingParams(temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS,
                                    structured_outputs=StructuredOutputsParams(json=OUTPUT_SCHEMA))

        def generate(chats):
            # thinking mode off (Qwen3-style templates; other templates ignore the flag)
            outs = llm.chat(chats, params, use_tqdm=False, chat_template_kwargs={"enable_thinking": False})
            return [o.outputs[0].text for o in outs]

        t0, base = time.time(), len(done_ids(out_path))

        def after_batch():
            ck.sync()
            done = len(done_ids(out_path))
            rate = (done - base) / max(time.time() - t0, 1e-9)
            eta = (total - done) / rate / 60 if rate > 0 else float("nan")
            print(f"PROGRESS {slug}: {done}/{total} ({done / max(total, 1):.0%}) | {rate:.2f} risk/s | ETA {eta:.1f} min", flush=True)

        every = EVERY if SMOKE else max(EVERY, CFG.get("batch") or 0)  # big GPUs: bigger batches
        stats = run_teacher(items, generate, out_path, every=every, limit=LIMIT,
                            meta={"model": model, "prompt_version": PROMPT_VERSION}, after_batch=after_batch)
        written += stats["written"]
        summary = {**stats, "model": model, "prompt_version": PROMPT_VERSION, "seconds": round(time.time() - t0),
                   "smoke": SMOKE, "gpu": gpu_info(), "gpu_config": CFG, "pins": pins, "max_tokens": MAX_TOKENS}
        ck.path(f"run_summary_{slug}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        ck.sync()
        print("TEACHER OK", json.dumps(summary), flush=True)
        del llm
        gc.collect()
        if torch.cuda.is_initialized():
            torch.cuda.empty_cache()
    s = run_summary(ck.local, JOB, started=STARTED, units_before=UNITS_BEFORE, units_after=UNITS_AFTER,
                    items_done=len(items), pins=pins,
                    extra={"models": MODELS, "smoke": SMOKE, "preset": PRESET, "gpu_config": CFG})
    ck.sync()
    print(json.dumps(s, indent=1))
    print(f"TEACHER DONE: {written} rows written, {round(time.time() - STARTED) // 60} min. Pull with: python scripts/gpu_jobs.py pull {JOB}", flush=True)


try:
    main()
except BaseException as exc:  # the GPU must not idle overnight after a crash
    print("TEACHER FAILED:", type(exc).__name__, str(exc)[:300], flush=True)
    raise
finally:
    unassign_runtime(UNASSIGN)
"""


def teacher() -> dict[str, Any]:
    """C2.2 / C2.3: the teacher notebook (bake-off with several models, or the full run with one)."""
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_teacher_notebook as legacy

    md = """# C2.2 / C2.3 - Teacher labels and plain-English rewrites (FinSight, Colab)

Runs AWQ teachers with **vLLM** over a risks file (`risk_id`, `title`, `body`). Inference only.
One JSON answer per risk: `category`, `seriousness_1to5`, `hard_fact`, `simple` (<= 60 words),
`numbers_copied`. Thinking mode is off, `max_tokens` is capped. The prompt and the loop are copied
from `finsight.risks` by `scripts/make_colab_notebooks.py`, so they are the tested ones.

**Pick `PRESET`, Run all.** Presets: `bakeoff_smoke` (20 risks per model), `bakeoff` (300 risks,
all candidates), `teacher_smoke`, `teacher_full` (12k, the chosen model), `gold_eval` (test-slice
gold sets: teacher + Qwen3.8, evaluation only). The quantisation kernel
and memory fraction come from the detected GPU (T4, L4, A100-40GB, A100-80GB, H100); a model that
does not fit the GPU is skipped.

- Inputs come from the private HF repo (`gpu_jobs.py push <job>`); every batch is uploaded back, so a
  rerun resumes from there. Progress lines show `PROGRESS ... ETA`; the end prints `TEACHER DONE`.
- The runtime disconnects itself at the end, also after a crash (`UNASSIGN`).
- Filters run on the laptop, not here. Teacher outputs are AI labels (`label_source`).
"""
    body = "import json\n\n" + legacy.prompt_cell()
    cells = [
        cell("markdown", md),
        cell("code", TEACHER_PARAMS, ["parameters"]),
        cell("code", TEACHER_INSTALL),
        cell("code", COMMON_CELL),
        cell("code", legacy.RUN_SOURCE.read_text(encoding="utf-8"), ["teacher-run"]),
        cell("code", body, ["teacher-prompt"]),
        cell("code", TEACHER_MAIN, ["teacher-main"]),
    ]
    return notebook(cells)


STUDENT_PARAMS = """
# ---- parameters (edit, then Run all) ------------------------------------------------------
PRESET = "student_smoke"           # student_smoke (10 steps, no GGUF) | student (full run + GGUF)
JOB = "student"                    # job folder: train.jsonl and dev.jsonl are its inputs
IO = "hf"                          # "hf" (private job repo, default) | "drive" (fallback)
JOBS_REPO = "AkshatTm/finsight-gpu-jobs"
MODEL = "Qwen/Qwen3-4B-Instruct-2507"   # Apache-2.0, non-thinking; the zero-shot bake-off may change it
PRECISION = "bf16"                 # "bf16": LoRA on a bf16 base (L4/A100); "nf4": 4-bit QLoRA, the T4 recipe
EPOCHS = 2
LEARNING_RATE = 2e-4
BATCH_SIZE = None                  # None = from the GPU (effective batch 16): G4/A100-80 16x1, A100-40 8x2, L4/T4 2x8
GRAD_ACCUM = None
MAX_SEQ = 1024
SAVE_STEPS = 200
SEED = 2026
PRESETS = {
    "student_smoke": {"smoke": True, "export_gguf": False},   # 64 train / 16 dev rows, 10 steps
    "student": {"smoke": False, "export_gguf": True},
}
SMOKE, EXPORT_GGUF = PRESETS[PRESET]["smoke"], PRESETS[PRESET]["export_gguf"]
UPLOAD = False                     # True: push adapter + GGUF (never merged fp16) to a private HF repo
HF_REPO = "AkshatTm/finsight-student-4b"
UNITS_BEFORE = None
UNITS_AFTER = None
UNASSIGN = True                     # disconnect the runtime when the job ends
"""

STUDENT_SETUP = """
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "peft>=0.13", "bitsandbytes>=0.45",
                "huggingface_hub"], check=True)
# Colab ships torchao 0.10, which peft rejects (needs >= 0.16); LoRA does not use it.
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], check=False)
"""

STUDENT_MAIN = """
# One function, so a crash also releases the GPU (UNASSIGN).
def main():
    import json, random, shutil, time
    from pathlib import Path
    import numpy as np
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
    from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer,
                              TrainerCallback, TrainingArguments)

    assert PRECISION in ("bf16", "nf4"), PRECISION
    gpu_name, gpu_gb, gpu_cap = gpu_probe()
    tier = gpu_tier(gpu_name, gpu_gb)
    auto_bs = {"G4": (16, 1), "H100": (16, 1), "A100-80GB": (16, 1), "A100-40GB": (8, 2)}.get(tier, (2, 8))
    bs, accum = BATCH_SIZE or auto_bs[0], GRAD_ACCUM or auto_bs[1]
    print(f"PRESET {PRESET} | GPU {tier} {gpu_gb:.0f} GiB | {PRECISION} | batch {bs} x accum {accum}", flush=True)
    JOBIO = JobIO(JOB, IO, hf_repo=JOBS_REPO, token=hf_secret())
    out = Path("/content/student")
    out.mkdir(parents=True, exist_ok=True)
    ck = JOBIO.checkpointer(every=10**9)  # synced on every save (SyncToDrive callback)
    ckpt_dir = ck.local / "trainer"

    train_rows, dev_rows = read_rows(JOBIO.fetch_input("train.jsonl")), read_rows(JOBIO.fetch_input("dev.jsonl"))
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
        per_device_train_batch_size=bs, per_device_eval_batch_size=bs,
        gradient_accumulation_steps=accum, learning_rate=LEARNING_RATE, lr_scheduler_type="cosine",
        warmup_steps=max(1, int(0.03 * math.ceil(len(train) / (bs * accum)) * EPOCHS)), fp16=(PRECISION == "nf4"), bf16=(PRECISION == "bf16"), gradient_checkpointing=True,
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
    keep = ck.local  # the job's out/ folder (synced to the HF repo or Drive below)
    shutil.copytree(adapter, keep / "adapter", dirs_exist_ok=True)
    shutil.copy(out / "metrics.json", keep / "metrics.json")
    if EXPORT_GGUF:
        shutil.copy(gguf, keep / gguf.name)
    ck.sync()
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
    s = run_summary(ck.local, "student", started=STARTED, units_before=UNITS_BEFORE, units_after=UNITS_AFTER,
                    items_done=len(train), pins={"torch": torch.__version__}, extra={"precision": PRECISION, "smoke": SMOKE, "preset": PRESET, "batch": [bs, accum]})
    ck.sync()
    print(json.dumps(s, indent=1))


try:
    main()
except BaseException as exc:  # the GPU must not idle after a crash
    print("STUDENT FAILED:", type(exc).__name__, str(exc)[:300], flush=True)
    raise
finally:
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
- Checkpoints go to local disk and are copied to the private HF job repo (or Drive) on every save (`SAVE_STEPS`); a disconnect resumes.
- Then the adapter is merged **temporarily** to make a **GGUF Q4_K_M** with llama.cpp. The merged fp16
  weights are deleted. Only the adapter and the GGUF are kept (job repo / Drive) and, with `UPLOAD`, pushed to a
  **private** Hugging Face repo. Never merged fp16.
- The teacher rewrites are AI-made, and the corpus terms are non-commercial: keep the repo private.
- Smoke first (`PRESET = \"student_smoke\"`), then `PRESET = \"student\"` (G4 recommended: fastest, about the same units as an L4).
"""
    cells = [
        cell("markdown", md),
        cell("code", STUDENT_PARAMS, ["parameters"]),
        cell("code", STUDENT_SETUP),
        cell("code", COMMON_CELL),
        cell("code", legacy.prompt_cell(), ["student-prompt"]),
        cell("code", legacy.PREP, ["student-prep"]),
        cell("code", STUDENT_MAIN, ["student-main"]),
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
