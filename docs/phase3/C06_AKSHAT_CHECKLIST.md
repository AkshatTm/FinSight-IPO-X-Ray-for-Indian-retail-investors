# C06 — Akshat's checklist (short form; ask Claude chat about any item)

## 1. Before Phase 3 starts (setup)

- [ ] Put this folder in the repo at `docs/phase3/` and push (or let C0.1 do it).
- [ ] **Colab:** disconnect idle sessions; in Drive create `MyDrive/FinSight/` (subfolders are made by notebooks). The 200 compute units expire 90 days after purchase: GPU jobs should not wait.
- [ ] **Colab:** check you can get each runtime type (T4, L4, A100) — just connect and disconnect.
- [ ] **Hugging Face:** create a write token; create a private model repo (or let the helper create them); save the token in `.env` as `HF_TOKEN` (never paste it in chat).
- [ ] **Hugging Face in Colab:** add the same token as a Colab secret named `HF_TOKEN`.
- [ ] **Kaggle:** confirm `kaggle kernels list --mine` works on the laptop; phone-verified account (GPU on).
- [ ] **Laptop:** ≥ 15 GB free disk for new PDFs and parsed outputs (the fetcher stops below 15 GB); Ollama stopped during batch jobs.
- [ ] **Frontier apps:** Claude.ai paid plan with Opus; ChatGPT Go active; turn **memory/personalisation and web search off** in both; note your plan names (recorded with every run, with the exact model string).
- [ ] **Google Cloud:** check the remaining trial credit in the console once; then do nothing until C5.1 (stay on the free trial, do not upgrade, no resources).
- [ ] **Calendar:** block time for the hand-work in §2 (it is on the critical path).
- [ ] Read C01 and C04 once so the bench rules make sense to you.

## 2. During Phase 3 (hand-work, in roughly this order)

| Part | Task | Approx. time |
| --- | --- | --- |
| C0.2 | Run the Colab rate-check + vLLM smoke notebook on T4, L4, A100; type the unit readings | 20–30 min |
| C1.1 | Approve the IPO list (remove odd ones) | 15 min |
| C1.2 | Download by hand any PDFs the script couldn't fetch | depends |
| C1.4 | Confirm split counts before freezing | 5 min |
| C3.1/C3.2 | **Verify gold v3** (10 showcase IPOs, pre-filled) | ~1.5 h |
| C2.1 | Segmentation spot-check (50) + E13b boundaries | ~40 min |
| C2.2 | Run teacher bake-off on Colab; rate 100 blind rows | Colab babysit + 30 min |
| C2.3 | Run the full teacher on Colab; rate quality-100 | Colab babysit + 30 min |
| C4.1 | **Verify gold v4 (Task A + red-flag inputs) + Q&A keys** for the 4 new bench IPOs; keys for the other 4; **TOC page ranges** for all 8 | ~8.5 h |
| C4.3 | **Frontier runs**: Opus + ChatGPT Go per bench document (+ bench-dev while C4.5 is above the cut line) | ~35 min per document per app (~9 h) |
| C2.4 | Verify category gold-150 | ~45 min |
| C2.5 | Run the student 4B on Colab (large classifier and 8B are cut) | Colab babysit |
| C2.5 | Rate gold-50 rewrites (blind) | ~45 min |
| C2.6 | Rate 60 novelty pairs | ~20 min |
| C4.4 | Blind-rate bench Tasks C + D (20 % repeated items; optional classmate second rater on 20 %) | ~2.5 h |
| C3.5 | Pick the IPOs that lead the class demo | 10 min |
| C3.7 | Decide the "red flags in chat" guard question; hand-check E7 samples | ~40 min |
| any | Approve copy and Hindi strings piling up in `AKSHAT_TODO.md` | ~1 h total |

**Colab babysitting** = start the run from its `COLAB_STEPS_<job>.md`, glance at it occasionally, copy outputs back when it finishes, disconnect the runtime.

**Hours per gate** (estimates): CG0 ~1.5 · CG1 ~2–3 · CG2 ~3 · CG3 ~2 · CG4 ~2.5 · **CG5 ~19** · CG6 ~1 → **~31 h** in total. Bench + gold v4 are about 60 % and are the biggest time risk (C05 §6). Start C4.1 as soon as CG1 passes.

## 3. After the build (finish)

- [ ] Decide deployment on the Google Cloud trial (C08); set the budget alert first; say "go" only when ready.
- [ ] Read every module's section in `docs/10_FINSIGHT_EXPLAINED.md` (viva is solo).
- [ ] Rewrite the report in your own voice; own every claim; check every number against `eval_results/`.
- [ ] Slides, demo video, demo rehearsal with the newest IPOs.
- [ ] Practise viva questions aloud.
- [ ] Cancel Google AI Pro auto-renewal if you don't want it to continue; check Google Cloud billing shows no running resources.
