# FinSight L4 GPU job for Cloud Run (B3.3a, optional `cloud_gpu` profile, B02 §10.3).
# vLLM serves the AWQ student on localhost; the FinSight worker drains the simplification queue
# through the OpenAI-compatible client (generate.vllm_backend), then the container exits.
# Build (from the repo root):  docker build -f deploy/gpu.Dockerfile -t finsight-gpu-worker .
# Large image (CUDA + vLLM): built only by the manual images workflow, never in PR CI.
FROM vllm/vllm-openai:v0.30.0

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    FINSIGHT_PROFILE=cloud_gpu \
    FINSIGHT_ROOT=/app \
    FINSIGHT_PATHS__MODELS_DIR=/models \
    FINSIGHT_SIMPLIFY__VLLM_URL=http://127.0.0.1:8000 \
    STUDENT_DIR=/models/simplifier/awq

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY configs ./configs

# FinSight gets its own Python 3.11 env, so vLLM's packages are left untouched.
RUN uv python install 3.11 \
 && uv venv --python 3.11 /app/.venv \
 && uv sync --frozen --no-dev --no-default-groups --group api --group cloud

COPY deploy/gpu_entrypoint.sh /app/gpu_entrypoint.sh
RUN chmod +x /app/gpu_entrypoint.sh

ENTRYPOINT ["/app/gpu_entrypoint.sh"]
