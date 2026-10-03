# 11 Reproducibility statement

> **DRAFT — Akshat to rewrite in his voice and to run the clean-clone check himself (roadmap, Tue 27 Oct).**

**Code and results.** Everything is in the public repository: code (`src/finsight/`), tests (`tests/`),
configs (`configs/`), result files (`eval_results/`), decision records (`docs/09_DECISIONS.md`) and the
notebooks used on Kaggle (`notebooks/`). The result tables in the README are generated from
`eval_results/` by a script, not typed.

**Seeds and runs.** The fine-tuned QA model and the BiLSTM-CRF were each trained with seeds 13, 42 and 2026;
the product uses seed 2026, chosen on dev. The bootstrap uses 1,000 resamples over IPOs with a fixed seed (2026).
Every result file stores its git SHA and creation time.

**Environment.** Python 3.11, `uv sync` from `uv.lock`. Dependency groups keep the API image free of torch
(`dev`, `api`, `data` by default; `ml`, `asr`, `onnx`, `tables` on request, ADR-029). Tasks run through
`uv run poe test | lint | typecheck | api`. The laptop is a 16 GB RAM machine with an RTX 2050 (4 GB).
Training ran on Kaggle GPUs only, started from the command line with the official `kaggle` CLI (ADR-042);
notebooks, parameters and the quality gate against the baseline are in the repository.

**What cannot be reproduced from the repository alone.**
- **The PDFs** are public SEBI and exchange filings but are not redistributed; `configs/demo_ipos.yaml`
  lists each file with its page count, date and SHA-256.
- **The weak-label corpus** (CC BY-NC-SA 4.0) is downloaded from its Hugging Face page, and the
  fine-tuned weights are not published for the same reason.
- **Gold labels, question sets and the guard set** were drafted by Claude and checked by the author
  (README of this folder lists the disclosures); the files are in `data/gold/` and committed.
- **LLM sampling.** Answers use temperature 0.2; a 13-item score can move by two or three between
  runs (ADR-020). E7 numbers are one run, not a mean.
- **The recorded demo answers** (`data/demo_cache/`) are real outputs of the `full` profile,
  never edited; they are the answers the public demo replays.

**Phase 2 additions.**
- **Generated, not edited.** Kaggle notebooks are generated from the code they run
  (`scripts/make_*_notebook.py`) and a test fails if a committed notebook drifts. The docs pages and the
  §7.9 table are generated from `eval_results/` (`uv run poe docs-gen --check` in CI).
- **Teacher labels** carry `label_source = teacher:<model>:<prompt_version>`; the teacher run appends its raw
  answers to a checkpoint file in batches, and a rerun resumes from it instead of starting again.
- **Provisional values.** `configs/risklevel.yaml` and `configs/compare.yaml` hold placeholder thresholds and
  reference quantiles (`provisional: true`) until the corpus runs; any number computed with them must be
  reported as provisional.
- **Fixture pack.** Tests on real document text use `tests/fixtures/real/` (short excerpts of public filings,
  B-ADR-15), so the Phase 2 code can be tested without the PDFs.
- **Cloud.** The deployment is code (`deploy/gcp/`, rendered by `scripts/render_deploy.py`); the container
  images are built and smoke-tested in CI. Nothing is deployed at the time of writing.

**Check.** From a clean clone: `uv sync`, `uv run poe test`, then `uv run python -m finsight.evaluate.ladder`
regenerates `ladder_table.*` from the stored per-row results without a GPU.
