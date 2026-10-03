# Morning report

## Overnight cloud run 1 (3–4 Oct 2026)

### What merged
- **PR #136 (B0.2):** Phase 2 docs, execution plan, CLAUDE.md rules, gold v3 template.
- **B0.3 (#122):** hosting is now **Google Cloud** (Cloud Run in Singapore, `asia-southeast1`; optional L4 GPU job). Azure is gone from every doc.
  - Config: `cloud` and `cloud_gpu` profiles, plus upload limits (50 MB, 1,500 pages, 3 per user per day, 10 per day overall) and the `UPLOADS_ENABLED` kill switch.
  - Env names: `.env.example` lists them; `scripts/check_env.py` tells you which ones are still missing.
  - Setup steps for you: `docs/phase2/HOSTING_SETUP_STEPS.md`.
  - Nothing was deployed and billing is untouched.

- **B1.1a (#125): upload checks.**
  - The app can tell whether an uploaded PDF is an RHP, a DRHP or a final Prospectus.
  - It rejects files that are too big, have too many pages, are password-locked or scanned, or aren't offer documents, with the reason codes the UI will show.
  - Tested on made-up PDFs. Real PDFs come in B1.1b on your laptop.

- **B1.2 (#127): the backbone for uploads.**
  - Files go to local disk or a Google Cloud bucket. Jobs, events and quotas live in SQLite on the laptop or Supabase Postgres in the cloud.
  - Processing runs stage by stage. A failed stage still leaves a partial report.
  - The live progress stream can resume where it left off.
  - Limits: 3 uploads per person per day and 10 overall, plus an off switch. Files are deleted after 30 days.
  - Google sign-in tokens are checked on the server.
  - CI now also tests against a real Postgres.

### Blocked, and why
- **B1.3a, B1.4, B2.1a** need the B0.4 fixture pack, which can only be made on your laptop.

### Your morning to-do, in order
1. Local session: **B0.4 fixture pack**. The L1 prompt is in `docs/AKSHAT_TODO.md`. It unblocks three cloud parts.
2. Local session: **B0.1 workspace bug**. The L1 prompt is in `docs/AKSHAT_TODO.md`.
3. Hosting steps, Part A only: `docs/phase2/HOSTING_SETUP_STEPS.md` (Supabase with Google sign-in, Vercel, Kaggle check; about 45 min). **Don't** enable GCP billing yet.
4. After you put the 5 unseen RHPs in `data/raw/unseen/` (Wed 7): local **B1.1b**. The prompt is in `docs/AKSHAT_TODO.md`.
5. Optional, 5 min: the B1.2 local check (one showcase RHP through the new upload API). The prompt is in AKSHAT_TODO.
6. Gold v3 pre-fill with Claude chat (`data/gold/gold_v3_template.jsonl`), due Fri 9 Oct.

### Surprises
- Mumbai (`asia-south1`) Cloud Run L4 GPUs are invitation-only, so the plan uses Singapore.
- GCP free-trial credit does not cover GPUs.
- Free HF accounts can no longer create Docker Spaces, so the HF fallback is paid (PRO).
