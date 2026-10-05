# C08 — Deployment on Google Cloud (final stage, at C5.1)

Deployment happens **after CG6 (feature freeze)**, at C5.1, on the Google Cloud free trial, and only with Akshat's explicit "go" (C-ADR-10). It is below the cut line (C05 §6). This file records the facts and the choices to make then.

## 1. What we have

- **Google Cloud free trial (active):** trial credit, account type **Free Trial**. This corrects B-ADR-16's "credit used up" premise; until C5.1 the code stays local-only. Akshat confirms the remaining credit in the console before C5.1.
  - Trial accounts get **no GPU quota**. GPUs need an upgrade to a paid billing account plus a quota request; after upgrading, anything beyond the credit is billed to the card.
  - CPU services (Cloud Run, Cloud Storage) work on the trial without upgrading.
- **Code:** the Google Cloud deploy code removed in B-ADR-16 is in git history (Dockerfiles, `deploy/gcp/`, Cloud Run launcher, images workflow). It is restored path by path with `git checkout 458207c^ -- <paths>` and then updated, not rewritten. **Not** `git revert 458207c`: that commit also contains the quota/timezone bug fix, which a revert would undo.
- **Models built for CPU:** extractor and classifier as ONNX int8, student as GGUF Q4, chat model as small GGUF. The product can run without a GPU.

## 2. Options to decide at deploy time

| Option | What it gives | Cost / risk |
| --- | --- | --- |
| **A. CPU-only on the trial** | Public link, full product, slower rewrites (top 15 automatic, rest on click) | Covered by the credit; no billing risk |
| **B. Upgrade + one GPU service** | Faster rewrites | Needs upgrade + GPU quota approval; billing risk after credit → **budget alert + hard cap first** |
| **C. A for the public site + B only for the class demo window** | Fast demo, cheap otherwise | Same as B for the demo window; scale-to-zero afterwards |

## 3. Pre-deploy checklist (whichever option)

- Budget alert at 50 % / 90 % / 100 % of the trial credit; billing export on (before any resource exists).
- Upload limits, kill switch and quotas from Phase 2 config set for public use.
- Secrets in Secret Manager; nothing in the image or git.
- Showcase reports precomputed so the landing and demo IPOs open instantly.
- Smoke test (`scripts/cloud_smoke.py`, restored) on one new IPO; record cold start and stage timings → E23/E24 on the deployed stack.
- Afterwards: scale to zero when not demoing; check no instance is running.

## 4. Parts (added to C05 when we get here)

- C5.1a Restore and update deploy code (💻 L, O) — no deploy.
- C5.1b Deploy with Akshat running every command that creates a paid resource (💻 L + 👤 A, S) — only after "go".
- C5.1c E23/E24 on the deployed stack; README live link (💻 L, S).
