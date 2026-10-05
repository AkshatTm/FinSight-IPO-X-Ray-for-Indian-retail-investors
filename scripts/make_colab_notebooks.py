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


BUILDERS: dict[str, Callable[[], dict[str, Any]]] = {"c0_rate_check.ipynb": rate_check}


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
