#!/bin/sh
# L4 GPU job: start vLLM on localhost, wait until it answers, simplify one document, stop.
# DOC_ID comes as an env override (jobs.launcher); the model is read from the /models mount.
set -eu

vllm serve "$STUDENT_DIR" --served-model-name simplifier-awq --host 127.0.0.1 --port 8000 \
  --max-model-len 2048 --gpu-memory-utilization 0.85 &
VLLM_PID=$!
trap 'kill "$VLLM_PID" 2>/dev/null || true' EXIT

i=0
until curl -sf http://127.0.0.1:8000/health >/dev/null; do
  i=$((i + 1))
  if [ "$i" -gt 180 ]; then
    echo "vLLM did not start within 15 minutes" >&2
    exit 1
  fi
  sleep 5
done

/app/.venv/bin/python -m finsight.jobs simplify "$DOC_ID"
