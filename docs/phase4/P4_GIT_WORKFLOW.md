# Phase 4 — Git workflow for two agents

Both agents commit and **push their own work** (as in phases 1–3). They never push to each other's branches.

## Branches
| Branch | Who writes | Created from | Purpose |
|---|---|---|---|
| `main` | CC only (merges) | — | Always green. Tagged `v1.0` at start of Phase 4 |
| `p4/cc` | CC | `main` after `v1.0` tag | All CC product work. CC may use short-lived `p4/cc-<topic>` branches and merge them into `p4/cc` |
| `p4/argon` | ARGON | `main` right after the CC-01 install PR (a descendant of `v1.0` that carries the Phase 4 docs) | All ARGON work: `ml/`, labels, deliveries |

CC-01 creates both branches and pushes them before ARGON starts.

## Who may change which paths
| Path | CC | ARGON |
|---|---|---|
| product package, `frontend/`, `configs/`, `deploy/`, `scripts/`, `tests/` (except `tests/ml/`) | write | **read only** |
| `docs/phase4/*.md` (plan/specs/contract) | write (with Akshat's OK) | read only |
| `docs/phase4/comms/to_argon.md`, `PROGRESS_CC.md` | write | read only |
| `docs/phase4/comms/to_cc.md`, `PROGRESS_ARGON.md`, `docs/phase4/P4_EXECUTION_PLAN_ARGON.md` | read only | write |
| `ml/handoff/` | write (CC builds the pack) | read only |
| `ml/` (everything else), `tests/ml/` | read only | write |
| `data/gold/v4/`, `data/gold/sod_fixtures/`, `data/gold/event_labels/`, `data/gold/top_risks/` | read only | write |
| `data/platform_bench/` (gitignored, Akshat's sheet) | read | read |
| `eval_results/p4/argon/` | read | write |
| `eval_results/p4/cc/` | write | read |

Each agent only writes its own files, so merges between `p4/argon` and `p4/cc` should never conflict.

## Commit and push rules (both agents)
1. Commit after every green test run. Conventional commits: `feat:`, `fix:`, `data:`, `eval:`, `ml:`, `docs:`.
2. Prefix every commit with the task id: `feat(CC-05): parse SOD litigation table`, `ml(AR-04): student v2 notebook`.
3. Push to your own branch at least at the end of every session (`git push origin p4/cc` / `git push origin p4/argon`).
4. Never force-push. Never rewrite history. Never push to `main` (ARGON) or to `p4/argon` (CC).
5. Never commit: model weights, PDFs, `data/raw`, `data/processed`, notebook outputs, `.env`, Platform Bench sheet contents (copyrighted platform text — keep it gitignored; commit only scores).

## Integration (CC does it, once per evening, or when ARGON posts a delivery)
```
git fetch origin
git checkout p4/cc
git merge --no-ff origin/p4/argon   # ARGON only touched ml/, data/gold/*, eval_results/p4/argon, its own md files
<run full test suite>
gh pr create --base main --head p4/cc   # then: gh pr merge --merge once CI is green
```
**Phase 4 merges are PRs with a merge commit** (`gh pr merge --merge`), never rebase-merge: `p4/cc` contains merge commits from `p4/argon`, and CI must run on the result. This overrides the Phase 3 rebase-merge rule for Phase 4 branches only.

Then CC writes a line in `to_argon.md`: "Merged p4/argon@<sha> into main. ARGON: `git merge origin/main` into p4/argon before your next session."

ARGON pulls main into `p4/argon` at the start of every session (`git fetch && git merge origin/main`).

## Large files
Weights never go into git. ARGON's notebooks save weights to Akshat's Google Drive (and optionally a **private**
HF repo). Akshat downloads them into `models/<model_id>/<version>/` (gitignored). The delivery folder in git holds
only `MODEL_CARD.md`, `metrics.json`, `predict.py`, `requirements.txt`, and a `SHA256SUMS` of the weight files.

## Antigravity safety setting
Run ARGON in a mode that **asks before** `git push`, deleting files, or long-running commands until Akshat trusts the
flow (Turbo auto-runs everything). At minimum, deny `rm -rf`, `git push --force`, `git reset --hard`.
