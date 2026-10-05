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


BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {
    "c0_rate_check.ipynb": rate_check,
    "c2_teacher.ipynb": teacher,
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
