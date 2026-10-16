# FinSight Bench

`bench/v1/` is frozen (C-ADR-06, C-ADR-24): the files listed in `manifest.yaml` `frozen_files` never
change; a later version gets `bench/v2/`. `answers/` and `paste/` are outputs and may be filled.

| What | Where |
| --- | --- |
| Documents | 7 test-slice IPOs (`manifest.yaml` `ipos`, `configs/splits.yaml` `bench`) |
| Items | `v1/items/task_{a,c,d,g}.jsonl` (Task B uses the Task A fields) |
| Answer keys | `v1/keys/` (copied from Akshat-verified gold v3 and the status gold) |
| Prompts, exactly as sent | `v1/inputs/prompts.jsonl.gz` (templates in `v1/prompts/`) |
| Scoring rules | `v1/scoring.yaml`, `v1/pinned/redflags.yaml` |
| Answers | `v1/answers/<system>/answers.jsonl` + `run.json` |
| Results | `eval_results/c4/bench_*.json` (`uv run python scripts/bench_score.py`) |

Frontier models are evaluation only. They are never part of the product.

## Local systems (Claude Code or you, on the laptop)

```
uv run python scripts/bench_run.py --system rules_v1 --processed data/processed   # Ollama running
uv run python scripts/bench_run.py --system student
uv run python scripts/bench_run.py --system base
uv run python scripts/bench_score.py
```

## Teacher (Gemma-4-31B-it, Colab G4)

Follow `docs/phase3/COLAB_STEPS_bench_teacher.md` (about 15–25 min on a G4).

## Frontier models (you)

Plans used (fill in): Claude.ai plan: ________ · ChatGPT plan: Go

Before you start, in **both** apps: turn memory / personalisation **off** and web search **off**.

1. `uv run python scripts/bench_frontier.py export --system opus` (and again with `--system chatgpt_go`).
   This writes `bench/v1/paste/<system>/<IPO>__<task>__<n>.md` (about 30–40 bundles per app), an empty
   `.reply.md` next to each, and `run.yaml`.
2. For each bundle: open a **new chat**, select the model (Opus in Claude.ai; the default in ChatGPT
   Go), paste the whole `.md` file, send. Copy the **whole reply** (use the app's copy button) into the
   matching `.reply.md`. Write the start and end time (UTC is fine, or local with the zone) for that
   bundle in `run.yaml`.
3. Fill the top of `run.yaml`: app, plan, plan price per month in ₹, the model string the app shows,
   memory off / web search off (`true`).
4. `uv run python scripts/bench_frontier.py import --system opus` (and `chatgpt_go`). It prints
   any bundle whose reply is missing or lacks a `### <task id>` heading; fix those and run it again
   (already imported answers are kept).
5. `uv run python scripts/bench_score.py`, then commit `bench/v1/answers/` and `eval_results/c4/`
   (branch `data/c4.3-frontier-answers`).

Optional, Claude only, instead of the app: an API run sends each frozen prompt alone (no
bundling). It needs an Anthropic key in your environment (`ANTHROPIC_API_KEY`, never in the repo or
chat) or `ant auth login`; it is billed per token (`run.json` records the cost):

```
uv run --with anthropic python scripts/bench_frontier.py api --system opus --limit 3   # try 3
uv run --with anthropic python scripts/bench_frontier.py api --system opus
```

Claude Opus 5.5 accepts no `temperature` and always thinks, so this run pins `effort: medium`
instead of temperature 0; it is reported as its own system (`opus_api`).
