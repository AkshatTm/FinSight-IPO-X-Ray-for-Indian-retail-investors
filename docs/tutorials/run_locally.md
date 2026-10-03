# Run FinSight locally in 10 minutes

By the end you will have the API and the website running on your machine, first on mock data and then on the real API. Nothing here needs a GPU, a cloud account or any PDF.

## What you need

- Python 3.11 and [uv](https://docs.astral.sh/uv/)
- Node.js 22 and [pnpm](https://pnpm.io/)
- Git (on Windows, use Git Bash)

## 1. Get the code and the Python environment

```bash
git clone https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors.git
cd FinSight-IPO-X-Ray-for-Indian-retail-investors
uv sync
uv run poe test
```

`uv sync` installs the default groups (dev, api, data, ml-cpu). The test run takes about 20 seconds and skips the tests marked `local`, which need real documents or model weights.

## 2. See the website on mock data

```bash
cd frontend
pnpm install
NEXT_PUBLIC_USE_MOCKS=1 pnpm dev
```

Open <http://localhost:3000>. Every API call is answered by the mocks in `frontend/mocks/`, so the library, the workspace, Model Lab, the upload flow and the report page all work without a backend. The report data is synthetic ("Sample Ltd").

## 3. Run the real API

In a second terminal, from the repository root:

```bash
FINSIGHT_PROFILE=dev_light uv run poe api
```

The API listens on <http://localhost:8000>. Try <http://localhost:8000/api/health> and the interactive docs at <http://localhost:8000/docs>. The `dev_light` profile uses SQLite (`data/finsight.db`) and the local folder `data/store` instead of cloud services, and signs everyone in as one local user.

## 4. Point the website at the API

Stop the mock server and start it without mocks:

```bash
cd frontend
pnpm dev
```

The site now calls `http://localhost:8000` (Next.js rewrites `/api/*` there). The showcase IPOs appear only after their documents are built (see [Add a showcase IPO](../howto/add_showcase_ipo.md)); without them the library is empty and that is expected.

## 5. Chat needs a local model

Chat answers come from a local LLM through [Ollama](https://ollama.com). Install it, pull the profile's model (`ollama pull qwen3.5:0.8b` for `dev_light`), and ask a question in a workspace. Without Ollama, `/api/health` reports `degraded` and the chat says the model is unavailable.

## Next

- [Analyse your first IPO document](first_document.md)
- [Commands](../reference/cli.md) and [Configuration](../reference/config.md)
- Something failed? See [Troubleshooting](../troubleshooting.md).
