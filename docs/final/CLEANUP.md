# Disk clean-up (v1.1)

The project folder went from **55.3 GB to 20.2 GB**. The app runs as before: fast tests pass
(2189 passed, 1 skipped for ARGON's fixtures), and two showcase IPOs (Ather Energy, Groww) open
with facts, page images and cited chat answers. A stored upload report (Paras Healthcare) shows
all five tabs: Overview, Financials, Red flags, Risks, Compare.

Free space on C: went from 82 GB to 115.5 GB. That figure includes the Ollama and HF cache
removals outside the repo, and counts `.venv` and `node_modules` after their reinstall.

## Sizes

| Folder | Before | After |
|---|---:|---:|
| `data/` | 22.04 GB | 9.08 GB |
| `models/` | 19.91 GB | 5.30 GB |
| `.claude/worktrees/` | 6.95 GB | 0 |
| `.venv/` (reinstalled) | 4.80 GB | 4.85 GB |
| `frontend/` (reinstalled, `.next` rebuilt on first run) | 1.52 GB | 0.77 GB |
| caches, `site/`, logs | 0.15 GB | 0 |
| **Repo total** | **55.3 GB** | **20.2 GB** |
| `~/.cache/huggingface` (outside the repo) | 19.3 GB | 15.9 GB |
| `~/.ollama/models` (outside the repo) | 20.3 GB | 15.6 GB |

`.venv` and `node_modules` are mostly hardlinks into the shared uv and pnpm caches, so deleting
and reinstalling them barely changed free space.

## What went where, and how to get it back

### Regenerable (deleted)

| Item | Restore |
|---|---|
| Worktree `.claude/worktrees/c3-gold-v31` (its commit is already in `final`; its 11 untracked gold files are in `data/backup_2026-11-03/c3-gold-v31-untracked/`) | nothing to restore |
| `../FinSight-cc`, `.claude/worktrees/c3.1a-financials` (empty folders holding only links) | nothing to restore |
| `.venv` | `uv sync --inexact --group ml --group onnx` (`start.bat` does this) |
| `frontend/node_modules` | `cd frontend && pnpm install --frozen-lockfile` |
| `frontend/.next`, `.next-e2e`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `.hypothesis`, `.playwright-mcp`, `site/`, `__pycache__`, `*.log` | rebuilt automatically |

The worktree and `../FinSight-cc` held 23 junctions pointing at the real `models/`, `data/raw/`,
`data/store/`, the showcase folders in `data/processed/` and `frontend/node_modules`. These links
were removed first, one at a time and without recursion. The file count and byte total of every
target folder were checked to be unchanged before anything else was deleted.

### On Hugging Face (deleted locally)

| Item | Where it is | Restore |
|---|---|---|
| `models/student_8b` (8B GGUF + adapter; the app does not use it) | dataset `AkshatTm/finsight-gpu-jobs`, `student_8b/out/` (sha256 checked) | `hf download AkshatTm/finsight-gpu-jobs --repo-type dataset --include "student_8b/out/*" --local-dir hf_tmp`, then move `student_8b/out` to `models/student_8b` |
| Ollama `finsight-student8b:q4` | same GGUF | `ollama create finsight-student8b:q4 -f <Modelfile>` pointing at the GGUF |
| `models/risk_classifier/seed-*` (6 runs; the app's ONNX was exported from seed-42) | private model repo `AkshatTm/finsight-weights-archive`, `risk_classifier/` | `hf download AkshatTm/finsight-weights-archive --include "risk_classifier/*" --local-dir models` |
| `models/extractor_v2` | same repo, `extractor_v2/` | `... --include "extractor_v2/*" --local-dir models` |
| `models/extractor/seed-13`, `seed-42` (the app runs seed-2026) | same repo, `extractor/` | `... --include "extractor/*" --local-dir models` |
| `models/reranker_onnx/reranker_fp32.onnx` + its 172 external weight files | same repo, `reranker_onnx/` | `... --include "reranker_onnx/*" --local-dir models` |

All 217 files in `finsight-weights-archive` were checked against the local copies (size, plus
sha256 for LFS files or the git blob hash for small files) before deletion. The repo is private.

The fp32 reranker is unused while `reranker_int8.onnx` exists. `jobs/preflight.reranker_file`
tries int8 first and only falls back to fp32 when int8 is missing, and the int8 graph references
no external files. Chat itself reranks with the PyTorch `BAAI/bge-reranker-v2-m3` from the HF
cache.

### Rebuildable data (deleted)

| Item | Restore | Time |
|---|---|---|
| `data/processed/batch` (parse store of the 289-document universe; the app does not read it) | `uv run python scripts/batch_parse.py` (needs `data/raw/offer_docs`, which is kept) | about 1.5 h (sum of the recorded per-document wall times) |
| `data/processed/kaggle/output` (raw Kaggle downloads; copies of `models/*`) | `uv run python -m finsight.weaklabel.kaggle fetch <run> --username akshattmo`; all 20 notebooks still exist on Kaggle | minutes |

### HF cache (outside the repo, deleted)

`Systran/faster-whisper-medium`, `Systran/faster-whisper-small`,
`mobiuslabsgmbh/faster-whisper-large-v3-turbo` (the voice module is gone from the code), plus
stubs of `Qwen/Qwen3-32B-AWQ`, `Qwen/Qwen3.8-27B-FP8` and `google/gemma-4-31B-it-qat-w4a16-ct`.
Total 3.6 GB. They download again on first use.

## Kept on purpose

- **Models the app loads:** `models/extractor/seed-2026`, `models/risk_classifier/onnx` +
  `tfidf.joblib`, `models/reranker_onnx/reranker_int8.onnx`, `models/student` (4B, also in
  Ollama as `finsight-student:q4`), `models/guard_clf`.
- **Data:** the showcase IPO folders and uploads in `data/processed/`, `bank/` and
  `risk_bank/`; `data/raw/rhp`, `data/raw/prospectus` and `data/raw/offer_docs` (some BIR links
  are dead, so a re-fetch could not get all 289 back); `data/store`, `data/finsight.db`,
  `data/demo_cache`, `data/gold`, `data/backup_2026-11-03`, `eval_results/`, `docs/`.
- **HF cache:** `BAAI/bge-m3`, `BAAI/bge-reranker-v2-m3`, `deepset/deberta-v3-base-squad2`,
  `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, both docling models,
  `microsoft/deberta-v3-base`, the `Qwen/Qwen3-4B-Instruct-2507` tokenizer, and the tiny DeBERTa
  used by a test.

## Notes found along the way

- `AkshatTm/finsight-gpu-jobs` is a **public** dataset, and it holds the student adapters and
  GGUFs. Make it private on Hugging Face if that was not intended.
- `p4/argon` had 10 commits on no remote. It was pushed unchanged so they are backed up.
- `git gc` was not run.
- Run `start.bat` from Explorer or cmd. Running `pnpm dev` from Git Bash made Turbopack fail on
  `next/font/google` ("queries have exactly one entry"). The same command from cmd works.
