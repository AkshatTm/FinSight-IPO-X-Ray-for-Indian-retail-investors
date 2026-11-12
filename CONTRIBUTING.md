# Contributing to Vidura

Vidura is a finished course project (v1.1) with one maintainer (Akshat Tomar). Issues and pull requests are welcome: bug fixes, documentation, new red-flag checks, evaluation. Read this first so a change can be merged without a second round.

## Set up

```bash
uv sync --inexact --group ml --group onnx --group docs
uv run poe test                     # fast tests, the same as CI
uv run poe lint && uv run poe typecheck
cd frontend && pnpm install --frozen-lockfile && pnpm test
```

Name every group you need in one `uv sync`; without `--inexact` a sync drops the groups it does not name. Running the whole app: [Install](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/docs/getting-started/install.md) and [Run Vidura](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/docs/getting-started/run.md). Coding standards, tests and CI: [Developer guide](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/docs/development/index.md).

## The loop

1. **Issue first**, saying what and why. Use the bug or feature template.
2. **Branch** `<type>/<slug>` from fresh `main`, for example `fix/rf08-litigation-total`.
3. **Small green commits** in [Conventional Commits](https://www.conventionalcommits.org/) form, `type(scope): summary`, with `Refs #<issue>`. No "wip" or whitespace-only commits.
4. **Pull request** that closes the issue, using the template. For changes over about 50 lines, put a short plan (at most 15 lines) in the description.
5. **CI green** (backend, frontend, docs), then merge and delete the branch. Never force-push `main`.

The full rules used during the project are in [08_GIT_WORKFLOW.md](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/docs/08_GIT_WORKFLOW.md).

## Tests

- Every module ships with pytest tests; `vidura.normalize` also has property tests (Hypothesis).
- Tests that need full documents, the corpus or model weights are marked `@pytest.mark.local`; `poe test` and CI skip them.
- Frontend: Vitest for logic and components, Playwright on the mocks for flows.

## Docs as code

Docs change in the same pull request as the behaviour they describe.

- Numbers come from `eval_results/` through scripts, the API reference from `openapi.json`, the configuration reference from the settings and `configs/`. Never type them by hand: run `uv run poe docs-gen`, `uv run poe gen-openapi` and `cd frontend && pnpm gen:api`.
- `uv run poe docs-build` (strict) and `uv run python scripts/check_links.py` must pass.
- Public functions get Google-style docstrings; CI fails below 70 % coverage (`interrogate`).
- Non-obvious choices get a decision record ([decisions](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/docs/adr/index.md)).

## What will not be merged

- Investment advice or predictions: no buy, sell, apply or avoid wording (`configs/forbidden_phrases.yaml` is checked by tests). The risk level always carries its disclaimer.
- Hand-edited model outputs or evaluation results.
- Test-slice or bench documents in any training data, threshold or prompt (C-ADR-02; `tests/test_split_leakage.py`).
- Data outside `data/gold`, `data/manifests` and the fixture pack; PDFs; model weights; `.env` files; notebook outputs; files over 5 MB.
- Credentials of any kind ([SECURITY](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/SECURITY.md)).
- Closed-weight or paid model APIs at runtime: Vidura uses open-weight models only.

By contributing you agree that your code is released under the MIT licence ([LICENSE](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/LICENSE)) and that you follow the [Code of Conduct](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/CODE_OF_CONDUCT.md).
