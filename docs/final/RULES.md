> **Historical record (final session (v1.1)).** Kept as written; it may describe plans that changed or were cut. Current state: the [FinSight docs site](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/docs/index.md) and [FINAL_SCORECARD](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/final/FINAL_SCORECARD.md).

# Final session rules (Opus backend + Sonnet frontend)

Both sessions work in **this folder**, on branch **`final`**.
(`.claude/worktrees/c3-gold-v31` still exists; ignore it, nobody works there.)

## Git
- Nobody runs `checkout`, `switch`, `stash`, `reset`, `rebase`, `pull` or `merge`.
- Only **Opus** runs git-remote operations (`push`, `fetch`, PRs, tags).
- Commit with explicit paths only: `git add frontend/...` or `git add src/...`.
  Never `git add -A` or `git add .`.
- Small commits, Conventional Commits (`feat(final): ...`, `fix(final): ...`).

## Ownership
| Owner | Paths |
|---|---|
| Opus | `src/`, `configs/`, `scripts/`, `tests/` (non-frontend), `openapi.json`, `docs/final/CONTRACT.md`, `eval_results/` |
| Sonnet | `frontend/` (may regenerate API types from `openapi.json`) |

The API shape the frontend can rely on is in `docs/final/CONTRACT.md`.

## Running app
- The app on `:3000` (Next.js) and `:8000` (FastAPI) is shared.
- Only Opus restarts the backend.
- Nobody runs a second `next dev` or a `next build` while the dev server is running.
- The API is English-only. Hindi and voice are being removed (Step 3); the frontend should drop them too.
