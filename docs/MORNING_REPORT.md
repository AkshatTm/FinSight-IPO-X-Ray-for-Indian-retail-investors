# Morning report

## Overnight cloud run 1 (3–4 Oct 2026)

### What merged
- **PR #136 (B0.2):** Phase 2 docs, execution plan, CLAUDE.md rules, gold v3 template.
- **B0.3 (#122):** hosting is now **Google Cloud** (Cloud Run in Singapore, `asia-southeast1`; optional L4 GPU job). Azure is gone from every doc.
  - Config: `cloud` and `cloud_gpu` profiles, plus upload limits (50 MB, 1,500 pages, 3 per user per day, 10 per day overall) and the `UPLOADS_ENABLED` kill switch.
  - Env names: `.env.example` lists them; `scripts/check_env.py` tells you which ones are still missing.
  - Setup steps for you: `docs/phase2/HOSTING_SETUP_STEPS.md`.
  - Nothing was deployed and billing is untouched.

### Blocked, and why
- **B1.3a, B1.4, B2.1a** need the B0.4 fixture pack, which can only be made on your laptop.

### Your morning to-do, in order
1. Local session: **B0.4 fixture pack**. The L1 prompt is in `docs/AKSHAT_TODO.md`. It unblocks three cloud parts.
2. Local session: **B0.1 workspace bug**. The L1 prompt is in `docs/AKSHAT_TODO.md`.
3. Hosting steps, Part A only: `docs/phase2/HOSTING_SETUP_STEPS.md` (Supabase with Google sign-in, Vercel, Kaggle check; about 45 min). **Don't** enable GCP billing yet.
4. Gold v3 pre-fill with Claude chat (`data/gold/gold_v3_template.jsonl`), due Fri 9 Oct.

### Surprises
- Mumbai (`asia-south1`) Cloud Run L4 GPUs are invitation-only, so the plan uses Singapore.
- GCP free-trial credit does not cover GPUs.
- Free HF accounts can no longer create Docker Spaces, so the HF fallback is paid (PRO).
