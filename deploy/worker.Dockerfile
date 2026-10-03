# FinSight CPU worker for Cloud Run Jobs (B3.3a, B02 §10). One execution per document:
#   python -m finsight.jobs run        (DOC_ID / JOB_ID come as env overrides from the API)
#   python -m finsight.jobs simplify   (CPU fallback: the student as GGUF Q4 via llama.cpp)
#   python -m finsight.jobs sweep      (retention, on a schedule)
# Build (from the repo root):  docker build -f deploy/worker.Dockerfile -t finsight-worker .
FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    FINSIGHT_PROFILE=cloud \
    FINSIGHT_ROOT=/app \
    FINSIGHT_PATHS__MODELS_DIR=/models

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1=12.* \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY configs ./configs

# Everything a document needs on a CPU: parsing (data), the TF-IDF baseline and risk bank
# (ml-cpu), the ONNX int8 classifier (onnx), GCS + Postgres (cloud, api) and llama.cpp.
RUN uv sync --frozen --no-dev --no-default-groups \
      --group api --group cloud --group data --group ml-cpu --group onnx \
 && uv pip install --python .venv/bin/python "llama-cpp-python==0.3.19" \
      --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

RUN useradd -m -u 1000 app && mkdir -p /models && chown -R app /app
USER app

ENTRYPOINT ["/app/.venv/bin/python", "-m", "finsight.jobs"]
CMD ["run"]
