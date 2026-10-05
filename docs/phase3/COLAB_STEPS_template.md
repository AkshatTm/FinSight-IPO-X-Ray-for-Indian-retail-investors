# COLAB_STEPS_<job> template (copy, rename, fill the <> parts)

**Job:** <what it does> · **GPU:** <T4 | L4 | A100> · **Expected:** <hours> ≈ <units> units (rates: T4 ~1.07, L4 ~1.54, A100 ~6.77 units/h; `docs/phase3/C03_TRAINING.md` §4) · **Notebook:** `notebooks/colab/<file>.ipynb`

## Once (first Colab job only)
1. In Google Drive create `MyDrive/FinSight/` and copy `notebooks/colab/_common.py` into it.
2. Colab secret `HF_TOKEN` (key icon → Add secret → notebook access on), only for jobs that upload weights.

## Run
1. Upload the notebook to Colab (File → Upload notebook). Runtime → Change runtime type → **<GPU>**.
2. Upload the inputs to `MyDrive/FinSight/<job>/`: <files>.
3. Read your compute units in the Resources panel and type them into `UNITS_BEFORE` in the parameter cell.
4. **Smoke first:** set `SMOKE = True`, run all (T4, minutes). It must end with a `run_summary.json`.
5. Real run: `SMOKE = False`, run all. If the runtime disconnects, reconnect, run the first cells again and run all: the notebook resumes from the Drive checkpoints (you lose at most ~10 minutes).
6. When the last cell finishes, type the units into `UNITS_AFTER`, re-run the last cell, then **disconnect the runtime** (set `UNASSIGN = True` to automate).

## Bring back
- Copy from `MyDrive/FinSight/<job>/` to the repo: <output files> → `<destination>`.
- `run_summary.json` → `eval_results/c/` and run `uv run python scripts/log_compute.py eval_results/c/run_summary.json` (rename it first so files do not collide).
- Tell Claude: "<job> is back".

## If it goes wrong
- Out of memory: lower `MAX_MODEL_LEN` / batch size, or use the fallback in the notebook's parameter cell.
- `No GPU available`: try again later or take an L4; never debug on an A100.
- Stuck for > 15 minutes with no new lines in the output file: stop, copy the Drive folder, tell Claude.
