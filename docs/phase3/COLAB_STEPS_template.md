# COLAB_STEPS_<job> template (copy, rename, fill the <> parts)

**Job:** <what it does> · **GPU:** <T4 | L4 | A100-40GB | A100-80GB | H100> · **Expected:** <hours> ≈ <units> units (rates: T4 ~1.07, L4 ~1.54, A100 ~6.77 units/h; H100 not measured; `docs/phase3/C03_TRAINING.md` §4) · **Notebook:** `notebooks/colab/<file>.ipynb`

## Once (first Colab job only)
1. Colab secret `HF_TOKEN` (key icon → Add secret → **Notebook access on**). It is the same token as `.env`; it is read inside the notebook and never printed.
2. The private job repo `AkshatTm/finsight-gpu-jobs` is created by `scripts/gpu_jobs.py push` (no Drive copying). Drive mode (`IO = "drive"`) still works as a fallback: copy `notebooks/colab/_common.py` to `MyDrive/FinSight/` and the inputs to `MyDrive/FinSight/<job>/`.

## Before (laptop, Claude)
1. `uv run python scripts/gpu_jobs.py push <job>` uploads the inputs, `_common.py` and the notebooks.

## Run (you, or Claude through colab-mcp)
1. Upload `notebooks/colab/<file>.ipynb` to Colab (or open it from the job repo's `notebooks/` folder). Runtime → Change runtime type → **<GPU>**. Check which GPUs your plan lists; the notebook picks the quantisation kernel and `GPU_MEM` from the GPU it gets.
2. Parameter cell: set `PRESET` (<presets>), type `UNITS_BEFORE` from the Resources panel. Leave `UNITS_AFTER = None` (give it to `gpu_jobs.py pull --units-after` later). Run all.
3. Progress prints `PROGRESS ... ETA` after every batch. The notebook ends with `<JOB> DONE` and disconnects the runtime (`UNASSIGN = True`, also after a crash).
4. A disconnect is safe: reconnect, pick the same preset, run all; it resumes from the repo (at most one batch redone).

## Bring back (laptop, Claude)
- `uv run python scripts/gpu_jobs.py status <job>` shows progress; `... pull <job> --units-before <n> --units-after <n>` downloads the outputs to the paths below and logs the compute row.
- Tell Claude: "<job> is back".

## If it goes wrong
- Out of memory: lower `MAX_MODEL_LEN` or use `QUANT_OVERRIDE` / `MODELS_OVERRIDE`; a model that does not fit the GPU is skipped with a message.
- `No GPU available`: try again later or take an L4; never debug on an A100.
- No new `PROGRESS` line for > 15 minutes: stop the runtime, run `gpu_jobs.py status <job>`, tell Claude.
