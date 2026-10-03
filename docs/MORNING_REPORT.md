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

- **B1.5 (#131): the upload screens, running on mock data.**
  - You can sign in with Google (once Supabase is set up), drop a PDF, and watch every processing step.
  - My uploads lists your documents. Every rejection message from B05 is shown.
  - The Hindi strings are my drafts, for you to review.
  - The finished report page itself comes in B3.1.

- **B2.3a (#133): the teacher, ready to run on Kaggle.**
  - The big model (Qwen3-14B, 4-bit) will label every corpus risk with a category, a 1–5 seriousness and "already happened?", and rewrite it in plain English.
  - Its answers are saved every 100 risks, so a stopped Kaggle session just resumes.
  - Back on the laptop, filters throw out any rewrite that changes a number, gives advice, runs past 70 words, turns "may" into "will" or repeats another. Each drop is counted by reason.
  - A 100-row sheet is sampled for you to rate.
  - The no-advice phrase list (`configs/forbidden_phrases.yaml`) now also checks every UI string in the tests.
  - Nothing ran on a GPU tonight. The smoke → pilot → full run is the local part B2.3b, and its prompt is in AKSHAT_TODO.

- **B2.4a (#134): the risk-category classifier, ready to train.**
  - A quick baseline (TF-IDF + logistic regression) trains on the laptop in seconds. Two Kaggle notebooks fine-tune DeBERTa: base with 3 seeds, large with 1.
  - Train and dev are split by company, so no company's wording leaks into the score.
  - The winner is picked by dev macro-F1 and exported to a small int8 ONNX file, so the cloud worker runs it without PyTorch.
  - Training is the local part B2.4b; its prompt is in AKSHAT_TODO.

- **B2.5a (#135): the plain-English rewriter, ready to train.**
  - A small model (Qwen3-4B) will learn from the teacher's rewrites on Kaggle, then become a 4-bit file that runs on an ordinary CPU (about 15 seconds per risk).
  - Every rewrite must keep the original's numbers and certainty, contain no advice phrase, and stay under 70 words. Otherwise the reader sees the original.
  - The 15 most important risks are rewritten automatically; a click moves any other risk to the front.
  - There is an optional GPU path (vLLM) for when Google Cloud billing exists.
  - Training is the local part B2.5b; its prompt is in AKSHAT_TODO.
  - I chose Qwen3-4B-Instruct over Qwen3.5-4B as the default, because Qwen3.5-4B is a multimodal model with a new attention type, which is riskier to fine-tune on a T4. Qwen3.5-4B stays in the bake-off.

- **B2.2a (#144): what makes a risk unusual, and the risks API.**
  - Each risk is compared with past IPOs from 2018–2023, leaving out the company's own earlier filings, to say how common it is ("found in 4% of past IPOs").
  - Hedging words are counted. When a cautiously worded risk actually describes something that already happened, it gets a note.
  - The API now lists risks: most important first, by category, unusual only, or by search. A click on "explain in plain English" goes to the front of the queue.
  - The similarity cut-off (0.80) is a placeholder until your 60-pair check in B2.2b.

- **B2.6a (#146): seriousness and the overall risk level.**
  - Each risk gets high / medium / low seriousness from simple rules (category, a hard fact, a big number, boilerplate), and an importance used to order the list.
  - The document gets a low / medium / high **risk level** from red-flag points and rare serious risks, divided by the checks that could actually run, so missing data never looks like a clean record. Every point links to its reason.
  - The thresholds are **made-up placeholders** marked `provisional` until B2.6b computes them from 2018–2023 IPOs on your laptop.
  - Chat now answers "how risky is this IPO?" with the level and its reasons; "should I apply?" is still refused. One decision for you in AKSHAT_TODO ("red flags" questions).

### Blocked, and why
- **B1.3a, B1.4, B2.1a** need the B0.4 fixture pack, which can only be made on your laptop.

### Your morning to-do, in order
1. Local session: **B0.4 fixture pack**. The L1 prompt is in `docs/AKSHAT_TODO.md`. It unblocks three cloud parts.
2. Local session: **B0.1 workspace bug**. The L1 prompt is in `docs/AKSHAT_TODO.md`.
3. Hosting steps, Part A only: `docs/phase2/HOSTING_SETUP_STEPS.md` (Supabase with Google sign-in, Vercel, Kaggle check; about 45 min). **Don't** enable GCP billing yet.
4. After you put the 5 unseen RHPs in `data/raw/unseen/` (Wed 7): local **B1.1b**. The prompt is in `docs/AKSHAT_TODO.md`.
5. Optional, 5 min: the B1.2 local check (one showcase RHP through the new upload API). The prompt is in AKSHAT_TODO.
6. Gold v3 pre-fill with Claude chat (`data/gold/gold_v3_template.jsonl`), due Fri 9 Oct.
7. Sat 10 (after B2.1b): local **B2.3b** teacher run on Kaggle. The prompt is in AKSHAT_TODO; it stops for your go/no-go on the 100-row quality sheet.

### Surprises
- Mumbai (`asia-south1`) Cloud Run L4 GPUs are invitation-only, so the plan uses Singapore.
- GCP free-trial credit does not cover GPUs.
- Free HF accounts can no longer create Docker Spaces, so the HF fallback is paid (PRO).
