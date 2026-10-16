"""The teacher (Gemma-4-31B-it) on the frozen bench prompts, with vLLM on a Colab G4 (C4.1).

Self-contained: it runs on the Colab VM, not on the laptop (no ``finsight`` import). Steps are in
``docs/phase3/COLAB_STEPS_bench_teacher.md``:

    laptop:  uv run python scripts/gpu_jobs.py push bench_teacher
    Colab:   the two-line cell in the steps file downloads and runs this file as a process
    laptop:  uv run python scripts/gpu_jobs.py pull bench_teacher --units-before <n> --units-after <n>

It reads ``bench_teacher/in/prompts.jsonl.gz`` from the private job repo and writes
``bench_teacher/out/raw_teacher.jsonl`` (one answer per prompt, same fields as the laptop runs)
after every batch, so a disconnected run resumes; ``run_summary.json`` comes last. Each frozen
prompt is sent unchanged as one user turn, greedy (temperature 0, seed 2026), thinking off.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = "AkshatTm/finsight-gpu-jobs"
JOB = "bench_teacher"
MODEL = "google/gemma-4-31B-it"  # C-ADR-05
VLLM_PIN = "vllm==0.31.0"  # C0.2 pin (works on the G4)
MAX_MODEL_LEN = 8192
BATCH = 32
WORK = Path("/content/bench_teacher")


def main() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", VLLM_PIN], check=True)
    from huggingface_hub import HfApi, hf_hub_download
    from vllm import LLM, SamplingParams

    token = os.environ["HF_TOKEN"]  # passed in by the Colab cell; never printed
    api = HfApi(token=token)
    WORK.mkdir(parents=True, exist_ok=True)
    src = hf_hub_download(REPO, f"{JOB}/in/prompts.jsonl.gz", repo_type="dataset", token=token,
                          local_dir=str(WORK), force_download=True)  # fmt: skip
    prompts = [json.loads(x) for x in gzip.decompress(Path(src).read_bytes()).decode().splitlines()]
    out = WORK / "raw_teacher.jsonl"
    try:  # resume from the copy in the repo
        prev = hf_hub_download(REPO, f"{JOB}/out/raw_teacher.jsonl", repo_type="dataset",
                               token=token, local_dir=str(WORK / "prev"), force_download=True)  # fmt: skip
        out.write_bytes(Path(prev).read_bytes())
    except Exception:
        out.write_text("", encoding="utf-8")
    done = {json.loads(x)["prompt_id"] for x in out.read_text(encoding="utf-8").splitlines() if x}
    todo = [p for p in prompts if p["prompt_id"] not in done]
    print(f"PRESET bench_teacher | {len(prompts)} prompts, {len(todo)} to do", flush=True)

    def push(name: str) -> None:
        api.upload_file(path_or_fileobj=str(WORK / name), path_in_repo=f"{JOB}/out/{name}",
                        repo_id=REPO, repo_type="dataset")  # fmt: skip

    llm = LLM(model=MODEL, max_model_len=MAX_MODEL_LEN, gpu_memory_utilization=0.90, seed=2026,
              limit_mm_per_prompt={"image": 0, "video": 0})  # fmt: skip
    t_start = time.time()
    for start in range(0, len(todo), BATCH):
        batch = todo[start : start + BATCH]
        chats = [[{"role": "user", "content": p["text"]}] for p in batch]
        params = [SamplingParams(temperature=0.0, seed=2026, max_tokens=p["max_tokens"])
                  for p in batch]  # fmt: skip
        t0 = time.time()
        outs = llm.chat(chats, params, use_tqdm=False,
                        chat_template_kwargs={"enable_thinking": False})  # fmt: skip
        per = (time.time() - t0) / len(batch)  # batched: the mean per prompt, not a latency
        with out.open("a", encoding="utf-8", newline="\n") as fh:
            for p, o in zip(batch, outs, strict=True):
                fh.write(json.dumps({
                    "system": "teacher", "prompt_id": p["prompt_id"], "task": p["task"],
                    "ipo_id": p["ipo_id"], "text": o.outputs[0].text, "seconds": round(per, 3),
                    "seconds_kind": "batch mean", "model": MODEL, "error": None,
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }, ensure_ascii=False) + "\n")  # fmt: skip
        push("raw_teacher.jsonl")
        print(f"PROGRESS teacher: {start + len(batch)}/{len(todo)}", flush=True)
    import torch

    summary = {
        "preset": JOB, "model": MODEL, "vllm": VLLM_PIN, "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "prompts": len(prompts), "written_this_run": len(todo), "temperature": 0.0, "seed": 2026,
        "max_model_len": MAX_MODEL_LEN, "thinking": False, "wall_seconds": round(time.time() - t_start),
        "smoke": False, "single_run": True,
    }  # fmt: skip
    (WORK / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    push("run_summary.json")
    print("TEACHER DONE", flush=True)


if __name__ == "__main__":
    main()
