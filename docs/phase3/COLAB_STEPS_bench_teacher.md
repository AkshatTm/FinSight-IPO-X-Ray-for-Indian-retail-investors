# COLAB_STEPS_bench_teacher — the teacher on the frozen bench (C4.1)

**Job:** `google/gemma-4-31B-it` (C-ADR-05) answers every frozen bench prompt (`bench/v1/inputs/prompts.jsonl.gz`, 224 prompts: Tasks A, C, D, G) with vLLM, greedy (temperature 0, seed 2026), thinking off, each prompt unchanged as one user turn. **Evaluation only:** the bench IPOs are test-slice and never train or tune anything (C-ADR-02). **GPU:** G4 (the model is bf16, ~62 GB). **Expected:** model load ~5–8 min plus ~5–10 min of generation ≈ 2–3 units.

## Run
1. Laptop: `uv run python scripts/gpu_jobs.py push bench_teacher` (uploads the prompts and `scripts/bench_vllm_job.py` to the private job repo).
2. Colab: connect a **G4**, check the `HF_TOKEN` secret is on, note the units left (Resources panel), and run this one cell:

```python
import os, subprocess, sys
from google.colab import userdata, runtime
from huggingface_hub import hf_hub_download
tok = userdata.get("HF_TOKEN")
job = hf_hub_download("AkshatTm/finsight-gpu-jobs", "bench_teacher/in/bench_vllm_job.py", repo_type="dataset",
                      token=tok, local_dir="/content/_bench", force_download=True)
try:
    subprocess.run([sys.executable, job], env=dict(os.environ, HF_TOKEN=tok, PYTHONUNBUFFERED="1"), check=True)
finally:
    runtime.unassign()  # releases the GPU even on a crash
```

It prints `PROGRESS teacher: n/224` after every batch and ends with `TEACHER DONE`. A disconnected run resumes from the copy in the job repo when the cell is run again.

## Bring back
- Laptop: `uv run python scripts/gpu_jobs.py pull bench_teacher --units-before <n> --units-after <n>` → `bench/v1/answers/teacher/answers.jsonl` and `eval_results/c4/bench_teacher_run_summary.json` (also logged to `eval_results/c/compute_log.jsonl`).
- `uv run python scripts/bench_score.py`.
