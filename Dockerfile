# FinSight API for a CPU-only Hugging Face Space (P6.1, ADR-022). Not built or tested in CI.
# Build:  docker build -t finsight-api .
# Run:    docker run -p 7860:7860 -v "$PWD/dist/space:/app/bundle:ro" finsight-api
# Stage 1: llama-cpp-python built from source. The prebuilt "CPU" wheels on the project's own
# index are linked against musl and fail to load on Debian (found by the deploy CI job), and
# PyPI ships only the sdist. Portable flags: AVX2/FMA/F16C, which every Cloud Run x86 CPU has,
# and no -march=native, since the build machine is not the machine it runs on.
FROM python:3.11-slim-bookworm AS llama

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential=12.* cmake=3.25.* \
 && rm -rf /var/lib/apt/lists/*

ENV CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DLLAMA_CURL=OFF" \
    CMAKE_BUILD_PARALLEL_LEVEL=4

RUN pip wheel --no-cache-dir --no-deps --no-binary llama-cpp-python \
      "llama-cpp-python==0.3.36" -w /wheels

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
COPY --from=llama /wheels /wheels
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

# API group only (FastAPI, bm25s, numpy): no torch, no transformers, no PyMuPDF.
# Pillow is for page thumbnails; llama-cpp-python comes from the build stage above.
RUN uv sync --frozen --no-dev --no-default-groups --group api \
 && uv pip install --python .venv/bin/python pillow huggingface_hub \
 && uv pip install --python .venv/bin/python /wheels/llama_cpp_python-*.whl

COPY deploy/space/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# HF Spaces run the container as uid 1000
RUN useradd -m -u 1000 user && mkdir -p /app/models /app/bundle && chown -R user /app
USER user

EXPOSE 7860
ENTRYPOINT ["/app/entrypoint.sh"]
