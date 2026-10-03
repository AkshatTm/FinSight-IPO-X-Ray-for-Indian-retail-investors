# Contributing to FinSight

FinSight is a course project with one maintainer (Akshat). Issues and pull requests are welcome; read this first so a change can be merged without a second round.

## Set up

```bash
uv sync                      # Python 3.11 and the dev, api and data groups
uv run poe test              # fast tests (CI runs the same)
uv run poe lint && uv run poe typecheck
cd frontend && pnpm install && pnpm test
```

Model work needs `uv sync --group ml`; the docs site needs `uv sync --group docs`. Name every group you need in one `uv sync`, because a sync drops the groups it does not name. More: [Run FinSight locally](docs/tutorials/run_locally.md).

## The loop

The full rules are in [`docs/08_GIT_WORKFLOW.md`](docs/08_GIT_WORKFLOW.md). In short:

1. **Issue first**, titled with the roadmap part (for example `B3.2 Compare`).
2. **Branch** `<type>/<part>-<slug>` from fresh `main`, for example `feat/b3.2-compare`.
3. **Small green commits** in [Conventional Commits](https://www.conventionalcommits.org/) form, `type(scope): summary`, with `Refs #<issue>`. No "wip" or whitespace-only commits.
4. **Pull request** that closes the issue; for changes over about 50 lines, put a short plan (at most 15 lines) in the description. Use the template in `.github/pull_request_template.md`.
5. **CI green, then rebase-merge** (every commit lands on `main`) and delete the branch. Never force-push `main`.

## Tests

- Every module ships with pytest tests; `finsight.normalize` also has property tests (hypothesis).
- Tests that need full documents, the corpus or model weights are marked `@pytest.mark.local`; `poe test` and CI skip them.
- Frontend: Vitest for logic and components, Playwright on the mocks for flows.

## Docs as code

Docs change in the same pull request as the behaviour they describe ([B09](docs/phase2/B09_DOCUMENTATION_STANDARDS.md)).

- Numbers come from `eval_results/` through scripts; the API reference from `openapi.json`; the configuration reference from the settings. Never type them by hand: run `uv run poe docs-gen`, `uv run poe gen-openapi` and `cd frontend && pnpm gen:api`.
- Public functions and classes get Google-style docstrings; CI fails below 70 % coverage (`interrogate`).
- `uv run poe docs-build` must pass with no warnings.
- Non-obvious choices get a proposed decision record (`B-ADR-NN` in `docs/phase2/B08_DECISIONS.md`).

## What will not be merged

- Investment advice or predictions: no buy, sell, apply or avoid wording (`configs/forbidden_phrases.yaml` is checked by tests). The risk level always carries its disclaimer.
- Hand-edited model outputs or evaluation results.
- Data outside `data/samples`, `data/gold` and the fixture pack, PDFs, model weights, `.env` files, notebook outputs, or any file over 5 MB.
- Credentials of any kind. See [SECURITY.md](SECURITY.md).
- Closed-weight model APIs at runtime: FinSight uses open-weight models only.

By contributing you agree that your code is released under the MIT licence ([LICENSE](LICENSE)) and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
