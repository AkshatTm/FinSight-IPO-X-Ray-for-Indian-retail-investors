#!/bin/sh
# Start the API on a Space. The data bundle and the GGUF model arrive as Space files / downloads:
#   /app/bundle  <- the folder made by scripts/bundle_artifacts.py (uploaded to the Space repo)
#   VIDURA_GGUF <- downloaded once from the Hugging Face Hub when it is missing
set -eu

MODEL_REPO="${VIDURA_GGUF_REPO:-unsloth/Qwen3.5-2B-GGUF}"
MODEL_FILE="${VIDURA_GGUF_FILE:-Qwen3.5-2B-Q4_K_M.gguf}"

if [ ! -f "$VIDURA_GGUF" ]; then
  echo "downloading $MODEL_REPO/$MODEL_FILE"
  /app/.venv/bin/python - <<PY
import os, shutil
from huggingface_hub import hf_hub_download
path = hf_hub_download(repo_id=os.environ.get("VIDURA_GGUF_REPO", "$MODEL_REPO"),
                       filename=os.environ.get("VIDURA_GGUF_FILE", "$MODEL_FILE"))
shutil.copyfile(path, os.environ["VIDURA_GGUF"])
PY
fi

cd /app/bundle
exec /app/.venv/bin/uvicorn vidura.api.app:app --host 0.0.0.0 --port "${PORT:-7860}"
