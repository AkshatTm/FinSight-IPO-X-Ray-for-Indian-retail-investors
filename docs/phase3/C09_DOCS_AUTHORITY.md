# C09 — Documentation authority and phase alignment

This guide resolves phase drift between older planning docs and the current Phase 3 codebase.
Use it when README, contributor docs, and phase docs appear to disagree.

## 1) Source of truth by topic

| Topic | Canonical source | Why this is canonical |
| --- | --- | --- |
| Active roadmap, part order, and dependencies | `docs/phase3/C05_ROADMAP.md`, `docs/phase3/C_EXECUTION_PLAN.md`, `PROGRESS.md` ("Resume here") | These files define the current Phase 3 execution sequence and the next unblocked part. |
| Runtime profiles and local/cloud behavior | `configs/config.yaml`, `src/finsight/core/config.py`, `src/finsight/jobs/launcher.py`, `src/finsight/storage/local.py` | Code and config show only `dev_light`, `full`, `deploy_cpu`, local storage, and in-process job launch. |
| Cloud policy | `docs/phase3/C_DECISIONS.md` (C-ADR-10), `docs/09_DECISIONS.md` (B-ADR-16 note) | B-ADR-16 removed cloud runtime code; C-ADR-10 clarifies trial status and deploy-only use. |
| Developer workflow | `CONTRIBUTING.md`, `docs/08_GIT_WORKFLOW.md`, `docs/phase3/C05_ROADMAP.md` | Contributing rules stay stable, while part IDs and branch examples must match Phase 3. |
| Generated technical reference | `openapi.json`, `scripts/gen_openapi.py`, `scripts/docs_gen.py`, `pyproject.toml` (`poe docs-gen`, `poe docs-build`) | API/config/reference docs are generated and validated from repository artifacts. |

## 2) How to treat older phase documents

- Phase 1 (`docs/00_README.md`) and Phase 2 (`docs/phase2/B00_README.md`) are historical context unless a Phase 3 file explicitly points back to a section.
- If a historical file conflicts with Phase 3 decisions, prefer Phase 3 docs plus current code/config.
- Keep historical docs intact unless the change is a factual correction that prevents wrong operational guidance.

## 3) Documentation update checklist (for PRs)

1. Confirm runtime claims against `configs/config.yaml` and `src/finsight/core/config.py`.
2. Confirm job/storage claims against `src/finsight/jobs/launcher.py` and `src/finsight/storage/local.py`.
3. Confirm roadmap/part references against `docs/phase3/C05_ROADMAP.md`, `docs/phase3/C_EXECUTION_PLAN.md`, and `PROGRESS.md`.
4. Regenerate references when needed: `uv run poe docs-gen`, `uv run poe gen-openapi`.
5. Validate docs build when docs content changes materially: `uv run poe docs-build`.

## 4) Current canonical summary

- FinSight runs locally for development and evaluation (`dev_light`, `full`, `deploy_cpu` profiles).
- Upload processing runs in-process via a local launcher thread.
- Cloud runtime code remains removed; deployment work is deferred to Phase 3 C5.1 under C-ADR-10 controls.
