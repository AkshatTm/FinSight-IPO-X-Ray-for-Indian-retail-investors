# Install

FinSight runs on one Windows laptop: the API, the upload pipeline, the web app and the models. This
page sets it up from zero. It was written on the reference machine: Windows 11, 16 GB RAM, an
NVIDIA RTX 2050 with 4 GB.

## 1. Tools

| Tool | Version used | Check | Get it |
| --- | --- | --- | --- |
| Git (with Git Bash) | any recent | `git --version` | <https://git-scm.com> |
| uv (installs Python 3.11 for you) | 0.12.7 | `uv --version` | <https://docs.astral.sh/uv/> |
| Node.js | 24 (CI uses 24) | `node -v` | <https://nodejs.org> |
| pnpm | 12.8.1 (`packageManager` in `frontend/package.json`) | `pnpm -v` | `npm i -g pnpm` |
| Ollama | 0.40.6 | `ollama --version` | <https://ollama.com/download> |

`start.bat` checks for `uv`, `pnpm` and `ollama` and stops with a link if one is missing.

## 2. Code and Python packages

```bash
git clone https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors.git
cd FinSight-IPO-X-Ray-for-Indian-retail-investors
uv sync --inexact --group ml --group onnx
```

`uv sync` installs the default groups (`dev`, `api`, `data`, `ml-cpu`); `ml` adds CUDA 12.8 PyTorch
and `onnx` adds ONNX Runtime for the classifier. `start.bat` runs the same command on every start, so
this step only saves time later. Add `--group docs` to build this site.

!!! note "Name every group in one command"
    `uv sync` without `--inexact` removes groups you did not name. If a test suddenly cannot import
    `fitz` or `onnxruntime`, run the command above again.

## 3. Model files

Weights are not in git (`models/` is ignored). The app needs:

| What | Where it must be | How to get it |
| --- | --- | --- |
| Plain-English student, Qwen3-4B LoRA as GGUF Q4_K_M (2.5 GB) | `models/student/simplifier-q4_k_m.gguf` | `hf download AkshatTm/finsight-gpu-jobs student/out/simplifier-q4_k_m.gguf --repo-type dataset --local-dir models/_dl`, then move the file to `models/student/` |
| Ollama model `finsight-student:q4` | Ollama's store | created from the GGUF on first start by `uv run python scripts/run_app.py --no-frontend` (uses `deploy/ollama/Modelfile.student`) |
| Risk classifier, ONNX fp32 | `models/risk_classifier/onnx/` (`model.onnx`, `tokenizer.json`, `labels.json`) | not on Hugging Face; copy from the owner's machine or rebuild ([model card](../model_cards/risk_classifier.md)) |
| Risk bank (past risks for "unusual") | `data/processed/bank/` | not published; rebuilt by `scripts/build_risk_bank.py` from the corpus |
| `BAAI/bge-m3`, `BAAI/bge-reranker-v2-m3` | Hugging Face cache | downloaded on first use when online |

The download command for the student was checked with `--dry-run` (1 file, 2.5 GB). Without the
classifier or the embeddings, the upload page asks whether to analyse without them and marks the
report as incomplete ([Reading the results](../user-guide/reading-results.md#incomplete-reports)).

## 4. Frontend packages

`start.bat` runs `pnpm install --frozen-lockfile` in `frontend/` the first time. To do it yourself:

```bash
cd frontend && pnpm install --frozen-lockfile
```

## 5. Check

```bash
uv run poe test
```

The fast suite skips tests that need full documents or weights (`local`, `slow`, `postgres` marks).
On the reference laptop it ran 2,189 tests in 8 min 25 s with 1 skipped (7 Nov 2026).

Next: [Run FinSight](run.md).
