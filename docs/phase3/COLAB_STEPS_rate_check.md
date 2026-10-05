# COLAB_STEPS_rate_check — vLLM smoke on the L4 (and optional re-check of rates)

**Job:** confirm the vLLM pin with a small AWQ model, once. **GPU:** **L4 only** (`awq_marlin` needs compute capability 8.0+; T4 cannot run it). **Expected:** ~10 minutes ≈ 0.3 units. **Notebook:** `notebooks/colab/c0_rate_check.ipynb`

The compute-unit rates are already measured and logged (T4 ~1.07, L4 ~1.54, A100 ~6.77 units/h; C03 §4). Re-run on T4/A100 with `RUN_VLLM = False` only if you want a second reading.

## Run
1. Upload `_common.py` to `MyDrive/FinSight/` and the notebook to Colab. Runtime → **L4 GPU**.
2. Parameter cell: `RUN_VLLM = True`; type `UNITS_BEFORE` (Resources panel).
3. Run all. The vLLM cell tries each pin in `VLLM_CANDIDATES`, installing and loading `Qwen/Qwen3-4B-AWQ` with `awq_marlin`; the first that prints `GEN_OK` is the pin. Expect a few minutes per candidate.
4. Type `UNITS_AFTER`, re-run the last cell, disconnect the runtime.

## Bring back
- `MyDrive/FinSight/rate_check/run_summary.json` → `eval_results/c/rate_check_l4.json`, then `uv run python scripts/log_compute.py eval_results/c/rate_check_l4.json`.
- Tell Claude "vLLM pin is back" and paste the `vllm_pin` value (and any error text if none worked). Claude then writes the pin into C03 §2.7 and the teacher notebooks.
- If **no candidate** works: paste the error tail; fallback is the old `vllm==0.8.5.post1` with `VLLM_USE_V1=0`, or transformers + AutoAWQ at lower throughput.
