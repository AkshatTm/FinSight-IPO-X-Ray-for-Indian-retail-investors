# FinSight CPU worker for Cloud Run Jobs (B3.3a, B02 §10). One execution per document:
#   python -m finsight.jobs run        (DOC_ID / JOB_ID come as env overrides from the API)
#   python -m finsight.jobs simplify   (CPU fallback: the student as GGUF Q4 via llama.cpp)
#   python -m finsight.jobs sweep      (retention, on a schedule)
# Build (from the repo root):  docker build -f deploy/worker.Dockerfile -t finsight-worker .
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

# Stage 2: the runtime image.
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
COPY --from=llama /wheels /wheels
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY configs ./configs

# Everything a document needs on a CPU: parsing (data), the TF-IDF baseline and risk bank
# (ml-cpu), the ONNX int8 classifier (onnx), GCS + Postgres (cloud, api) and llama.cpp.
RUN uv sync --frozen --no-dev --no-default-groups \
      --group api --group cloud --group data --group ml-cpu --group onnx \
 && uv pip install --python .venv/bin/python /wheels/llama_cpp_python-*.whl

RUN useradd -m -u 1000 app && mkdir -p /models && chown -R app /app
USER app

ENTRYPOINT ["/app/.venv/bin/python", "-m", "finsight.jobs"]
CMD ["run"]
