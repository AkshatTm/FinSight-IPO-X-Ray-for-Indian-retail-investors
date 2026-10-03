# FinSight API for Google Cloud Run (B3.3a, B-ADR-04). CPU only: no torch, no transformers.
# Build (from the repo root):  docker build -f deploy/api.Dockerfile -t finsight-api .
# Run locally:  docker run -p 8080:8080 -e FINSIGHT_PROFILE=dev_light finsight-api
# Chat uses llama.cpp with a GGUF from the /models mount; the showcase bundle is mounted at
# /app/bundle, which then becomes FINSIGHT_ROOT (deploy/gcp/api-service.yaml). Without the bundle
# the image still starts with its own configs/. Nothing here holds a secret.
FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    FINSIGHT_PROFILE=cloud \
    FINSIGHT_ROOT=/app \
    FINSIGHT_PATHS__MODELS_DIR=/models \
    PORT=8080

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1=12.* \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY configs ./configs

# api (FastAPI, SQLAlchemy, psycopg, JWT), cloud (GCS client), data (PyMuPDF and Pillow for page
# images). llama-cpp-python comes as a prebuilt CPU wheel, so no compiler is needed.
RUN uv sync --frozen --no-dev --no-default-groups --group api --group cloud --group data \
 && uv pip install --python .venv/bin/python "llama-cpp-python==0.3.19" \
      --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

RUN useradd -m -u 1000 app && mkdir -p /app/bundle /models && chown -R app /app
USER app

EXPOSE 8080
CMD ["/bin/sh", "-c", "exec /app/.venv/bin/uvicorn finsight.api.app:app --host 0.0.0.0 --port ${PORT} --timeout-keep-alive 30"]
