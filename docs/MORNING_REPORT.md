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

- **B3.3a (#148): everything needed to put FinSight on Google Cloud, written as files. Nothing is deployed.**
  - Three container images: the website's API (small, no PyTorch), a worker that processes each uploaded document, and an optional GPU worker for the plain-English rewrites.
  - Cloud Run settings for each one. The API scales to zero when idle and to at most 2 copies, the GPU job is optional, and old uploads are deleted after 30 days. Secrets are never in the files.
  - After an upload, the API now really starts the worker on Cloud Run. If that fails, the reader sees an error instead of waiting forever.
  - Every PR now builds the two CPU images and runs a full smoke test (upload → processing → report) against the API container. Pushing images to Google is a button you press by hand, later.
  - Three runbooks: deploy, rollback and cost incident. The smoke deploy (B2.7) waits for your "go" and has its prompt in AKSHAT_TODO.

- **B3.2 (#150): the Compare tab.**
  - FinSight reads the peer table that every offer document has in "Basis for Offer Price": P/E, EPS, return on net worth and book value of the listed companies the issuer compares itself with.
  - If the RHP leaves the issuer's P/E blank, it is worked out from the price.
  - Issue size, OFS share, insider price gap and P/E are placed among past IPOs ("Higher than 65% of past IPOs").
  - The tab works on made-up mock data. The past-IPO numbers are placeholders until a laptop run computes them; the prompt is in AKSHAT_TODO.
  - It also fixed a hidden API bug: two different "Evidence" shapes had the same name, so the API description mixed them up. A test now catches this.

- **B3.1 (#151): the report page.**
  - Opening an uploaded document now shows its report: the company, the offer line, and four tabs (Overview, Red flags, Risks, Compare).
  - The risk-level card shows low / medium / high with up to three reasons you can click. Its disclaimer is always on screen; "How is this worked out?" opens the explanation from the UI spec.
  - Red flags are listed concerns first. Risks can be sorted, searched and filtered, and "Explain this" asks for a plain-English version, which appears on its own a few seconds later.
  - Everything runs on **made-up sample data** for now. Once the fixture pack exists, a short laptop session checks it against real documents and swaps in real samples; the prompt is in AKSHAT_TODO. A few new UI lines need your OK (AKSHAT_TODO, "New copy to review").

- **B4.1 (#153): the documentation website, complete for the cloud half.**
  - A docs website (MkDocs Material) builds from the `docs/` folder: getting-started tutorials, how-to guides (add a showcase IPO, add a fact, retrain the models, record the demo, deploy), a troubleshooting page with the 15 most likely problems, architecture diagrams, and runbooks for deploying, rolling back, cost incidents, rotating secrets, restoring the database and monitoring.
  - Nothing with a number is typed by hand. The settings, data formats, glossary and design-decision list are generated, and so are the numbers inside the evaluation page, the model cards (extractor, BiLSTM-CRF, MuRIL guard) and the datasheets (corpus, weak labels, gold sets). CI fails if any of them goes stale.
  - New project files: CHANGELOG, CONTRIBUTING, SECURITY, PRIVACY (checked against what the database really stores) and a code of conduct. The README now describes Phase 2.
  - Two real bugs fixed on the way: the JSON logs were never switched on (now on in Cloud Run, with document and job ids on failures), and the frontend's API address had two different names (now `FINSIGHT_API_ORIGIN` everywhere).
  - Docstring coverage went from 52 % to 84 %; CI now fails below 70 %.
  - Not published yet: putting the site on GitHub Pages is free but waits for your "go". Testing the runbooks once is a laptop follow-up.

- **B4.2 (#156): report drafts updated for Phase 2.**
  - `report/` now has drafts for the Phase 2 data, the method (upload pipeline, red flags, risk features, rewrites and their checks, risk level, compare, hosting), a results table for E13–E24 that is generated from `eval_results/` (every row says "not run yet" today, so no number is invented), and notes for error analysis and reproducibility.
  - Five new disclosures for the final report are listed in `report/README.md` (AI-made teacher labels, AI-pre-filled gold, provisional thresholds, outcome data only for checking, mock data on the report page).
  - Still yours: rewrite every section in your own voice; the result paragraphs get written once the laptop runs produce numbers.

- **B3.5a (#158): hardening, cloud half.**
  - A security review of the upload, storage, jobs and login code is in `docs/security_review.md` (15 checks). Three real holes were fixed: a local upload without a declared size could fill the server's memory; a too-big file sent to the cloud upload link was downloaded into the API before its size was checked; and the "Explain this" limit per person would have counted everyone as one person behind Vercel and Cloud Run. Two items stay open and are named for the parts that build them (a 10-minute parse timeout, removing personal contacts from risk text).
  - New tests fail every processing step in turn and check that only the steps depending on it are skipped, that error details never reach the browser, and that a retry redoes only what is missing.
  - Every job now records an estimated cost (run time × machine size × Google's list price). A new page, `/admin/costs`, shows per-day uploads, CPU seconds, the share of the monthly free allowance used and failed jobs. Only emails in `auth.admin_emails` can open it. The prices are marked provisional because Singapore is priced a little higher than the list price used.
  - The page's text is new (not in the UI spec), so it is listed for your OK in AKSHAT_TODO.

- **B3.4a (#160): Model Lab Phase 2 and the new site text.**
  - The Model Lab has seven new sections for the Phase 2 experiments (splitting risks, the financial checks, sorting risks, plain-English rewrites, unusualness, whether the risk level matches what happened, speed and cost). None appear yet: each one shows up by itself once your laptop runs write its result file. The file formats are written down in B06 §5 so the eval scripts know what to produce.
  - The "does the risk level match what happened?" section always shows when its file exists, even with a weak result. Its sentence ("no clear", "weak" or "moderate" relationship) is worked out from the numbers by code, never typed.
  - The landing page now leads with uploading ("Analyse an IPO document", "Explore a sample report"), adds the "What you get" blocks and the new "won't do" lines, and can show two new stats once they have real values. How it works has the eight-step upload row; About has the three new known limits. The English is the UI spec's; the Hindi is mine and waits for your OK.
  - One thing to decide: About still says "Covers 10 IPOs, not every IPO", which is no longer true for uploads (AKSHAT_TODO, "Needs your decision").

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
