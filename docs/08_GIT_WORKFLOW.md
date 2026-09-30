# 08 — Git and GitHub Workflow

**Goal:** a long, *meaningful* commit history and a visible PR/issue trail that reads like real engineering work, because it is. Every commit leaves the repo better and green. No padding.

---

## 1. How GitHub counts your contributions (so none are lost)

- Commits count only when they land on the **default branch (`main`)** and are authored with an **email linked to your GitHub account** (`git config user.email`).
- **Squash-merging collapses a PR's 8 commits into 1.** So we merge PRs with **rebase-merge** (`gh pr merge --rebase`), which keeps every commit on `main`.
- Opening **issues** and **pull requests** also counts as contributions. One issue + one PR per sub-phase ≈ 60+ extra honest contributions over the month.
- Claude Code may add a `Co-Authored-By` trailer to commits. That's fine: contribution credit goes to the commit author (you). If you'd rather not have it, check Claude Code's settings docs for the co-author option.
- Expected natural total: ~150–250 commits, ~40–50 PRs, ~40–50 issues by 1 Nov.

## 2. The loop for every sub-phase

```bash
# 1. Issue (title = roadmap sub-phase)
gh issue create --title "P1.4 Numeral normalization" --body "<scope + done-when from 07_ROADMAP.md>" --label phase-1,backend

# 2. Branch from fresh main
git switch main && git pull --rebase
git switch -c feat/p1.4-numerals

# 3. Work in small green steps (tests → code → commit), push often
git push -u origin feat/p1.4-numerals

# 4. PR that closes the issue
gh pr create --fill --title "feat(normalize): Indian numeral normalization (P1.4)" --body "Closes #14 ..."

# 5. CI green → merge keeping all commits, delete branch
gh pr merge --rebase --delete-branch

# 6. Tag at phase end
git switch main && git pull --rebase
git tag -a v0.1.0 -m "Phase 1: documents understood" && git push origin v0.1.0
gh release create v0.1.0 --title "v0.1.0 — Phase 1" --notes-file CHANGELOG_SNIPPET.md
```

Claude Code runs this loop. Akshat's only standing job: glance at each PR before its merge at gate sub-phases (P*.buffer and F8), and approve risky merges when asked.

## 3. Branch names

`<type>/<subphase>-<slug>` — e.g. `feat/p2.3-weaklabel`, `fix/p1.2-toc-offset`, `data/p0.4-recon`, `eval/p5.2-frontier`, `docs/p7-report`, `chore/p0.2-scaffold`. Frontend: `feat/f3-xray`.

## 4. Commit messages (Conventional Commits)

```
<type>(<scope>): <imperative summary, ≤ 72 chars>

<why this change; what it enables; anything surprising>
Refs #<issue>
```
Types: `feat`, `fix`, `test`, `refactor`, `perf`, `docs`, `data`, `eval`, `build`, `ci`, `chore`, `style` (formatting only, rare).
Scopes: package names (`core`, `parse`, `normalize`, `extract`, `weaklabel`, `retrieve`, `generate`, `verify`, `guard`, `voice`, `chat`, `evaluate`, `api`, `pipeline`) or `web`, `notebooks`, `docs`, `ci`.
Breaking API change: `feat(api)!: ...` + `BREAKING CHANGE:` footer.

### Good commits (each one is real progress)
```
test(normalize): add table-driven cases for lakh/crore/million scales
feat(normalize): parse Indian digit grouping and scale words
feat(normalize): apply table header scale "(₹ in million)" to cells
test(normalize): hypothesis round-trip across formatting styles
fix(normalize): treat [●] placeholders as Placeholder, never 0
docs(explained): add numeral normalization section
```

### Commit rules
1. **Commit when a test goes green** or a coherent step is complete — typically every 30–90 minutes of work.
2. One logical change per commit. Tests for a behaviour may land in the same commit or immediately before it.
3. `main` is always green: never merge a failing PR.
4. **Never** commit: data files outside `data/samples` and `data/gold`, PDFs, model weights, `.env`, notebook outputs, anything > 5 MB.
5. **No filler commits:** no "wip", "update", "fix typo" chains, whitespace-only commits, splitting one change into many, or empty commits. If a typo fix is needed, fold it into the next real commit or amend before pushing.
6. Rewrite local history (`git commit --amend`, interactive rebase) freely *before* pushing; never force-push `main`.

## 5. Pull requests

PR title = conventional commit style + sub-phase ID. Body template (`.github/pull_request_template.md`):
```markdown
## What
<2–4 bullets>
## Why
<link to roadmap sub-phase / PRD FR-id>
## How tested
- [ ] `uv run poe test` / `pnpm test`
- [ ] Slow tests (if models touched): <result>
- [ ] Screenshots/GIF (UI changes)
## Results (if eval)
<table or link to eval_results/*.json>
## Docs
- [ ] 07_ROADMAP.md boxes ticked · [ ] PROGRESS.md · [ ] 10_FINSIGHT_EXPLAINED.md section (new module)
Closes #<issue>
```

## 6. Issues and labels

Labels: `phase-0` … `phase-7`, `frontend`, `backend`, `ml`, `data`, `eval`, `bug`, `blocked`, `akshat` (needs human action), `p0`/`p1`/`p2`.
Bugs found during review → a `bug` issue with steps to reproduce; fixed in a `fix/...` branch.
Use a GitHub Project board (Todo / In progress / Review / Done) — optional, 5 minutes to set up, looks good on the profile.

## 7. Tags and releases (one per phase)

| Tag | When | Release title |
|---|---|---|
| `v0.1.0` | G1 | Documents understood (parsing, sections, numerals) |
| `v0.2.0` | G2 | Our model (weak labels, fine-tuned extractor, ladder) |
| `v0.3.0` | G3 | Trustworthy chat (retrieval, verifier, guard, voice, API) |
| `v0.4.0` | G4 | Full product locally (UI integrated, demo mode) |
| `v1.0.0-rc.1` | G5 | Deployed, feature freeze |
| `v1.0.0` | Sat 31 Oct | Final submission (report PDF attached) |

Release notes list merged PRs (`gh release create --generate-notes` works well) plus a 3-line summary and the headline numbers.

## 8. CI (GitHub Actions)

- `backend.yml`: uv setup → `poe lint` → `poe typecheck` → `poe test` (not slow). Runs on PRs and `main`.
- `frontend.yml`: pnpm install → lint → typecheck → vitest → build. Path-filtered to `frontend/**`.
- `e2e.yml` (from F8): Playwright against mocks.
- Status badges in README.

## 9. Repo hygiene for recruiters

README (from P6.3): one-line pitch, GIF of the tick-and-tie reveal, live link, architecture diagram (mermaid), results table (generated), how to run locally in 5 commands, licences, and a "What I learned" section. Pin the repo on your profile. Add topics: `nlp`, `rag`, `extractive-qa`, `distant-supervision`, `fintech`, `india`, `nextjs`, `fastapi`.
