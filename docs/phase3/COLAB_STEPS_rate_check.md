# COLAB_STEPS_rate_check — vLLM smoke on the L4 (and optional re-check of rates)

**Job:** confirm the vLLM pin with a small AWQ model, once. **GPU:** **L4** (any sm80+ GPU works: A100, H100; a T4 skips the vLLM test). **Expected:** ~10 minutes ≈ 0.3 units. **Notebook:** `notebooks/colab/c0_rate_check.ipynb`

The compute-unit rates are already measured and logged (T4 ~1.07, L4 ~1.54, A100 ~6.77 units/h; C03 §4). If an H100 is listed, a `rate_check` run on it gives its rate (and tells whether the pin also holds there).

## Before (laptop, Claude)
`uv run python scripts/gpu_jobs.py push rate_check` (uploads `_common.py` and the notebooks; the job has no inputs).

## Run
1. Colab: Runtime → Change runtime type → **L4 GPU** (note which GPUs are listed). Colab secret `HF_TOKEN` with notebook access on.
2. Open `c0_rate_check.ipynb`. Parameter cell: `PRESET = "rate_check"`; type `UNITS_BEFORE` from the Resources panel. Run all.
3. The vLLM cell tries each pin in `VLLM_CANDIDATES`, installing and loading `Qwen/Qwen3-4B-AWQ` with the kernel chosen for the GPU; the first that prints `GEN_OK` is the pin. Expect a few minutes per candidate. It ends with `RATE CHECK DONE. vllm_pin = ...` and disconnects the runtime.

## Bring back
- `uv run python scripts/gpu_jobs.py pull rate_check --units-before <n> --units-after <n>` → `eval_results/c/rate_check_run_summary.json` and a row in the compute log.
- Tell Claude "vLLM pin is back". Claude writes the pin into C03 §2.7 and the teacher notebook defaults.
- If **no candidate** works: paste the error tail; fallback is the old `vllm==0.8.5.post1` with `VLLM_USE_V1=0`, or transformers + AutoAWQ at lower throughput.
