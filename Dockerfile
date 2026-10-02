# FinSight API for a CPU-only Hugging Face Space (P6.1, ADR-022). Not built or tested in CI.
# Build:  docker build -t finsight-api .
# Run:    docker run -p 7860:7860 -v "$PWD/dist/space:/app/bundle:ro" finsight-api
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    FINSIGHT_PROFILE=deploy_cpu \
    FINSIGHT_ROOT=/app/bundle \
    FINSIGHT_GGUF=/app/models/model.gguf \
    FINSIGHT_RETRIEVE__RERANK=false \
    PORT=7860

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 curl \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

# API group only (FastAPI, bm25s, numpy): no torch, no transformers, no PyMuPDF.
# Pillow is for page thumbnails; llama-cpp-python comes from the CPU wheel index (no compiler).
RUN uv sync --frozen --no-dev --no-default-groups --group api \
 && uv pip install --python .venv/bin/python pillow huggingface_hub \
 && uv pip install --python .venv/bin/python llama-cpp-python \
      --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

COPY deploy/space/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# HF Spaces run the container as uid 1000
RUN useradd -m -u 1000 user && mkdir -p /app/models /app/bundle && chown -R user /app
USER user

EXPOSE 7860
ENTRYPOINT ["/app/entrypoint.sh"]
