"""Writes notebooks/b2_teacher_kaggle.ipynb (B2.3, teacher generation on a Kaggle T4).

    uv run python scripts/make_teacher_notebook.py                 # (re)write the notebook
    uv run python scripts/make_teacher_notebook.py kernel smoke --username <kaggle-user>
        # -> data/processed/kaggle/kernels/finsight-teacher-smoke/ for `kaggle kernels push -p`

The prompt, the JSON schema and the checkpoint loop are copied from ``finsight.risks`` when the
notebook is written, so the notebook can never drift from the tested code
(``tests/risks/test_teacher_notebook.py`` checks this). Runs: smoke = 50 risks, pilot = 500,
full = everything; each resumes from the ``raw.jsonl`` of an earlier run when it is attached.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finsight.risks import teacher  # noqa: E402

OUT = ROOT / "notebooks" / "b2_teacher_kaggle.ipynb"
RUN_SOURCE = ROOT / "src" / "finsight" / "risks" / "teacher_run.py"
DATASET = "finsight-teacher-risks"  # private Kaggle dataset: risks.jsonl (+ raw.jsonl to resume)
RUNS: dict[str, int | None] = {"smoke": 50, "pilot": 500, "full": None}

MD = """# B2.3 - Teacher labels and plain-English rewrites (FinSight, M5)

Runs a Qwen teacher (AWQ 4-bit) with **vLLM** over the corpus risks in the private dataset
`finsight-teacher-risks` (`risks.jsonl`: `risk_id`, `company`, `title`, `body`). Inference only;
nothing is trained here. One JSON answer per risk: `category` (one of 10), `seriousness_1to5`,
`hard_fact`, `simple` (<= 60 words), `numbers_copied`. Thinking mode is off.

- **Order:** smoke (50) -> pilot (500) -> full. Answers are appended to
  `/kaggle/working/teacher/raw.jsonl` every 100 risks; attach an earlier `raw.jsonl` as a dataset
  and the run skips what is done.
- **Filters run on the laptop**, not here (`python -m finsight.risks.teacher_data filter`), with
  the same checks the student's rewrites must pass.
- GPU: T4 (16 GB, fp16 compute; AWQ kernels work on Turing). With T4 x2 the model is split over
  both GPUs (more room for the KV cache). Record the GPU hours in PROGRESS.md.
- Teacher outputs are AI labels: every row the laptop writes carries `label_source`.
"""

PARAMS = """# ---- parameters ------------------------------------------------------------------------------
MODEL = "Qwen/Qwen3-14B-AWQ"  # Apache-2.0; fallback "Qwen/Qwen2.5-14B-Instruct-AWQ"
DATASET = "finsight-teacher-risks"
LIMIT = 50  # smoke 50 | pilot 500 | full None
EVERY = 100  # checkpoint interval (risks per vLLM batch)
MAX_MODEL_LEN = 4096
MAX_TOKENS = 400
OUT_DIR = "/kaggle/working/teacher"
"""

SETUP = """# vLLM 0.8.5 still has the V0 engine (xformers attention), which runs on a T4 (sm75).
# Newer releases may need the V1 engine; check the vLLM docs before changing the pin.
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "vllm==0.8.5.post1"], check=True)
"""

BODY = """import json, os, shutil, time
from pathlib import Path

os.environ.setdefault("VLLM_USE_V1", "0")
import torch
from vllm import LLM, SamplingParams

ON_KAGGLE = Path("/kaggle/input").exists()
if not ON_KAGGLE:  # a dry read of the files on the laptop; vLLM itself needs the GPU
    OUT_DIR = "teacher_out"
risks_file = next(Path("/kaggle/input").rglob("risks.jsonl")) if ON_KAGGLE else Path("data/processed/teacher/risks.jsonl")
out_path = Path(OUT_DIR) / "raw.jsonl"
out_path.parent.mkdir(parents=True, exist_ok=True)
earlier = list(Path("/kaggle/input").rglob("raw.jsonl")) if ON_KAGGLE else []
if earlier and not out_path.exists():
    shutil.copy(earlier[0], out_path)  # resume
    print("resuming from", earlier[0])

risks = list(read_jsonl(risks_file))
items = [{"risk_id": r["risk_id"], "messages": messages(r.get("title") or "", r["body"])} for r in risks]
print(len(items), "risks;", len(done_ids(out_path)), "already done; GPUs:", torch.cuda.device_count())

llm = LLM(model=MODEL, quantization="awq", dtype="float16", max_model_len=MAX_MODEL_LEN,
          gpu_memory_utilization=0.92, tensor_parallel_size=max(1, torch.cuda.device_count()),
          enforce_eager=False, seed=2026)
try:  # vLLM <= 0.10
    from vllm.sampling_params import GuidedDecodingParams
    params = SamplingParams(temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS,
                            guided_decoding=GuidedDecodingParams(json=OUTPUT_SCHEMA))
except ImportError:  # newer releases renamed it
    from vllm.sampling_params import StructuredOutputsParams
    params = SamplingParams(temperature=0.2, top_p=0.9, max_tokens=MAX_TOKENS,
                            structured_outputs=StructuredOutputsParams(json=OUTPUT_SCHEMA))

def generate(chats):
    outs = llm.chat(chats, params, use_tqdm=False,
                    chat_template_kwargs={"enable_thinking": False})
    return [o.outputs[0].text for o in outs]

t0 = time.time()
stats = run_teacher(items, generate, out_path, every=EVERY, limit=LIMIT,
                    meta={"model": MODEL, "prompt_version": PROMPT_VERSION})
elapsed = time.time() - t0
summary = {**stats, "model": MODEL, "prompt_version": PROMPT_VERSION, "limit": LIMIT,
           "seconds": round(elapsed), "gpus": torch.cuda.device_count(),
           "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
(Path(OUT_DIR) / "run_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print("TEACHER OK", json.dumps(summary))
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
    """The prompt and schema as literals, generated from ``finsight.risks.teacher``."""
    return (
        "# GENERATED from finsight.risks.teacher by scripts/make_teacher_notebook.py; do not edit\n"
        f"PROMPT_VERSION = {teacher.PROMPT_VERSION!r}\n"
        f"SYSTEM = {teacher.SYSTEM!r}\n"
        f"OUTPUT_SCHEMA = json.loads({json.dumps(teacher.OUTPUT_SCHEMA)!r})\n\n\n"
        "def messages(title, body):\n"
        '    text = f"Title: {title.strip()}\\n\\n{body.strip()}" if title.strip() else body.strip()\n'
        '    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]\n'
    )


def build() -> dict[str, Any]:
    return {
        "cells": [
            _cell("markdown", MD),
            _cell("code", PARAMS, ["parameters"]),
            _cell("code", SETUP),
            _cell("code", RUN_SOURCE.read_text(encoding="utf-8"), ["teacher-run"]),
            _cell("code", "import json\n\n" + prompt_cell(), ["teacher-prompt"]),
            _cell("code", BODY),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def kernel_folder(run: str, username: str, folder: Path) -> Path:
    """Rendered notebook + ``kernel-metadata.json`` for ``kaggle kernels push -p folder``."""
    from finsight.weaklabel.kaggle import CODE_FILE, render_notebook

    nb = render_notebook(build(), {"LIMIT": RUNS[run]})
    slug = f"finsight-teacher-{run}"
    meta = {
        "id": f"{username}/{slug}",
        "title": slug,
        "code_file": CODE_FILE,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",  # pip install vllm and the model download
        "dataset_sources": [f"{username}/{DATASET}"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / CODE_FILE).write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")
    (folder / "kernel-metadata.json").write_text(json.dumps(meta, indent=1) + "\n", "utf-8")
    return folder


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", nargs="?", default="write", choices=["write", "kernel"])
    p.add_argument("run", nargs="?", default="smoke", choices=list(RUNS))
    p.add_argument("--username")
    args = p.parse_args(argv)
    if args.command == "write":
        OUT.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8", newline="\n")
        print("wrote", OUT)
        return
    if not args.username:
        p.error("kernel needs --username (your Kaggle username; no token is read here)")
    folder = ROOT / "data" / "processed" / "kaggle" / "kernels" / f"finsight-teacher-{args.run}"
    print("wrote", kernel_folder(args.run, args.username, folder))


if __name__ == "__main__":
    main()
