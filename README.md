# FinSight — IPO X-Ray for Indian retail investors

[![backend](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/actions/workflows/backend.yml/badge.svg)](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/actions/workflows/backend.yml)

FinSight reads a Red Herring Prospectus (RHP) and shows a fact sheet where every figure is page-cited. A bilingual (English/Hindi) chat answers questions, and every number in an answer is checked against the document and marked ✅ verified, ⚠️ unverifiable or ❌ contradicted. Everything runs on open-weight models, locally first.

**Not investment advice.** FinSight summarises public disclosures and never recommends whether to apply for an IPO.

Course project for CSE472 (Deep Learning for NLP), due 1 November 2026. Work in progress: see [`PROGRESS.md`](PROGRESS.md) and [`docs/07_ROADMAP.md`](docs/07_ROADMAP.md).

## Run locally

```bash
uv sync                 # install (dev + api groups)
uv run poe test         # fast tests
uv run poe lint         # ruff check + format check
uv run poe typecheck    # mypy on core, normalize, verify
```

Model work needs `uv sync --group ml` (CUDA PyTorch) and, for voice, `--group asr`. Documentation index: [`docs/00_README.md`](docs/00_README.md).

## Licences

Code: MIT (see [`LICENSE`](LICENSE)). Training data and any model trained on it: CC BY-NC-SA 4.0, non-commercial (see [`NOTICE`](NOTICE)).
