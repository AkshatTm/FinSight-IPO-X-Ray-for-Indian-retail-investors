# C05 — Roadmap (gate-driven, no dates)

## 0. How to use this file

- Each part = one GitHub issue = one branch `<type>/c<x.y>-<slug>` = one PR (rebase-merge). Same Git rules as before (`docs/08_GIT_WORKFLOW.md`).
- **Where:** 💻 L = Claude Code local session · 🟠 G = Colab (Akshat runs) · 🔵 K = Kaggle (CLI from a local session, or Akshat) · 👤 A = Akshat by hand.
- **Model:** O = Opus (★ design-heavy or hard logic), S = Sonnet. A bug that failed twice on Sonnet → Opus. Model check before every part (CLAUDE.md step 3).
- A part may start when everything in **Needs** is merged/done. Pick the next unblocked part in this order: **GPU lane first** (never leave a ready GPU job waiting), then the critical path (§6), then the code lane.
- **Full scope:** nothing is cut (Akshat's decision, replacing the kickoff cuts of C-ADR-01). Every part below ships.
- End of part: tick the box, update `PROGRESS.md` "Resume here" (no dates), write hand-work to `docs/AKSHAT_TODO.md`, print `✅ <ID> done — run /clear and paste the Phase 3 resume prompt.`
- Phase 2 parts that are absorbed here are marked "(was Bx.y)"; tick them in B07 as "moved to Phase 3".

## 1. Three lanes run at the same time

| Lane | Runs | Rule |
| --- | --- | --- |
| **GPU lane** | Colab / Kaggle jobs | Always one job running if one is unblocked |
| **Code lane** | One Claude Code local session | One part per session, `/clear` between |
| **Akshat lane** | Ratings, gold checks, frontier runs | On the critical path; done in the gaps |

The **frontier runs (C4.3) do not need any FinSight model**, so Akshat can do them as soon as the bench is frozen — long before training finishes.

## 2. Parts

### C0 — Setup → gate CG0

- [x] **C0.1 Phase 3 docs + rules** · 💻 L · **O** · Needs: Akshat drops `docs/phase3/` in the repo
  Commit `docs/phase3/` and the kickoff-review fixes, Akshat approves the critical path (§6), apply the CLAUDE.md patch (C00 §5), record C-ADR-01…11 as proposed, mark absorbed B-parts in B07, create labels `colab`/`kaggle`, milestones CG0–CG6 and issues for all C0–C4 parts, reset `PROGRESS.md` "Resume here" for Phase 3.
  *Done when:* merged; issues and milestones exist.
- [x] **C0.2 Colab + HF + compute log** · 💻 L + 🟠 G · S · Needs: C0.1, Akshat setup (C06 §1)
  `notebooks/colab/_common.py` (Drive mount, local-disk checkpoints synced to Drive, resume helpers, run_summary), `docs/phase3/COLAB_STEPS_template.md`, `scripts/log_compute.py` → `eval_results/c/compute_log.jsonl`, HF private upload helper. A tiny smoke notebook Akshat runs once on T4, L4 and A100 to **record the real compute-unit rates** and **test the vLLM pin with a small AWQ model** (C03 §2.7); C03 §4 table updated from them.
  *Done when:* observed rates committed; budget table re-planned.
  *Status:* code merged; rates measured by hand and logged (T4 1.07, L4 1.54, A100 6.77 units/h), C03 §4 re-planned. **Left:** the vLLM pin test on the L4 (`COLAB_STEPS_rate_check.md`, in AKSHAT_TODO).

**CG0:** docs merged · Colab rates known · HF private repo works · Kaggle CLI works on the laptop. **Passed** (vLLM pin `vllm==0.31.0` on L4 + G4; teacher GPU G4).

### C1 — Newest-IPO data → gate CG1

- [x] **C1.1 IPO universe list** · 💻 L + 👤 A · S · Needs: CG0
  Build `configs/ipo_universe.csv` (C02 §2) for mainboard IPOs 2024 → latest; print the count by year and type. Akshat approves / removes rows.
  *Done when:* list approved and merged.
  *Status:* merged (overnight run, pre-approved counts): 289 rows from SEBI's public filings (`finsight.ingest.universe`, `scripts/build_ipo_universe.py`); exchange/listing date not available from SEBI (left `both`/empty); SME flagging moves to C1.3.
- [x] **C1.2 Downloader + fetch** · 💻 L · S · Needs: C1.1
  `scripts/fetch_offer_docs.py` (C02 §3) with tests on a fake server; run it; `status` filled; manual-download list printed for blocked sources.
  *Done when:* ≥ 90 % of approved rows `downloaded` or explained.
  *Status:* done: 289 docs fetched.
- [x] **C1.3 Batch parse + hardening** (was B1.1b) · 💻 L · S · Needs: C1.2
  `scripts/batch_parse.py` through `validated → parsed → sections → risks_split`; fix repeated failures with regression tests; `eval_results/c/parse_batch.json`.
  *Done when:* failures are fixed or listed with reasons; timings recorded.
  *Status:* done: 275 parsed, 14 excluded with reasons (12 SME, 2 unnumbered risks).
- [x] **C1.4 ★ Time split + leakage guard + rolling window** · 💻 L + 👤 A · **O** · Needs: C1.3
  One package: `finsight.splits`. Strict split → `configs/splits.yaml` (C02 §4; showcase roles from `demo_ipos.yaml`), the manifest format + retro manifests for Phase 1 artefacts in `data/manifests/`, `tests/test_split_leakage.py`, `configs/reference.yaml` + the `reference` API (eval and product windows, corpus by close year; C02 §5). **No wiring into other packages here:** C2.1 wires the bank + novelty, C2.7 weak labels, C2.8 risk level, C3.4 compare. Akshat confirms the counts before freezing.
  *Status:* code merged (C1.4 code-only PR: `finsight.splits`, CLI `python -m finsight.splits build [--freeze]`, `tests/test_split_leakage.py`). Real-data run done on Sonnet: Akshat confirmed the counts, `--freeze` written (`configs/splits.yaml`, 4 manifests in `data/manifests/`), leakage tests run and pass. `bench` is empty until C4.1 sets it.
  *Done when:* split frozen; leakage test green in `poe test`.
- [x] **C1.5 BIR link check + backfill** · 💻 L · S · Needs: CG0
  Count live links → `eval_results/c/bir_links.json`: 855 links 2009-2023, 48 answer as direct PDFs, 780 are HTML filing pages (SEBI/exchange), 27 dead. Backfill done (`scripts/backfill_bir_pdfs.py`, `eval_results/c/bir_backfill.json`): PDF files 0 → 40 (340 MB, one per `mapping_key`) in the new gitignored `data/raw/bir_backfill/`; nothing reads it and no split or eval set changed. The HTML pages would need the C1.2 fetcher's page-to-PDF step.

**CG1:** split frozen · every new document parsed or excluded with a reason · leakage test green.

### C2 — Training → gates CG2, CG3

- [x] **C2.1 Risk bank + E13** (was B2.1a-left + B2.1b) · 💻 L (+ 🔵 K if slow) · S · Needs: CG1, Akshat's segmentation spot-check
  Golden tests on fixture pages; segment `train`+`dev`; bge-m3 bank with `ipo_id`/`doc_date`/`split` + manifest; separate eval parquet for test/bench; wire `risks.bank`/`novelty` to the `splits.reference` window; E13/E13b; teacher input export (cap 25 per company, target min(12k, achievable)) + manifest.
- [x] **C2.2 ★ Teacher bake-off** · 💻 L + 🟠 G + 👤 A · **O** · Needs: C2.1 · done: Gemma-4-31B-it (C-ADR-05, G4; Qwen3.8-27B-FP8 and Qwen3-32B-AWQ as the other candidates)
  `COLAB_STEPS_teacher_bakeoff.md`; Qwen3-14B-AWQ vs Qwen3-32B-AWQ (L4-only fallback in C03); 300 risks × 2 teachers; filters; blind sheet (100 rows); Akshat rates; ADR → `eval_results/c/teacher_bakeoff.json`.
- [x] **C2.3 Teacher full run** (was B2.3b) · 💻 L + 🟠 G + 👤 A · S · Needs: C2.2 · run done on the G4 (12,000 risks, 10,892 kept); **CG2 passed** (quality-100: faithful 98 %, category correct 94 %)
  ≈12k `train` risks on Colab A100; filters; quality-100 from the full output; go/no-go.
- [x] **C2.3b Teacher data clean-up** · 💻 L · S · Needs: CG2
  Strict number filter (scale/unit and sign vs the source) over the kept rows; deterministic category remap for the themes quality-100 found inconsistent + one rule per theme in the teacher category guide; non-risk title count; seriousness distribution (4 + 5 → "severe" if level 5 < ~100).
  *Status:* done: `finsight.risks.teacher_cleanup`, `configs/category_remap.yaml`, `eval_results/c/teacher_cleanup_report.json`. 10,891 of 10,892 pairs kept, 799 categories remapped, 22 non-risk titles, severe band = 488 (level 5 has 17).
- [ ] **C2.7 Extractor v2** · 💻 L + 🔵 K · S · Needs: CG1 (runs in parallel with C2.2–C2.3)
  Weak labels over `train` incl. 2024+ (wires `weaklabel` to manifests); Kaggle 3 seeds; ladder row `qa_finetuned_v2`; keep only if it wins on dev.

**CG2:** teacher output accepted (≥ 85 % "same meaning: yes" on quality-100) · datasheet updated.

- [x] **C2.4 Classifier** (was B2.4b) · 💻 L + 🔵 K + 👤 A · S · Needs: CG2, C2.3b, gold-150
  TF-IDF; base 3 seeds (Kaggle); large 3 seeds (Colab); base must beat TF-IDF on dev; ONNX; E16; model card. Seriousness scored with MAE, within-1 accuracy and severe-band recall.
  - [x] TF-IDF 0.862 · [x] base 3 seeds: dev macro-F1 0.892 ± 0.006 (beats TF-IDF), gold-150 0.899 (best seed 0.881, acc 0.933) · [x] seriousness dev MAE 0.186, within-1 0.997, severe recall 0.56 (gold-150 best seed: MAE 0.14, severe recall 0.75 on 4 rows) · [x] E16 · [x] ONNX **fp32** (int8 broke DeBERTa-v3: agreement 0.05, best 0.82; `eval_results/c/classifier_onnx_int8_attempt.json`) · [x] model card
  - [x] large 3 seeds on the Colab G4 (~1 h 25 m): dev macro-F1 0.894 ± 0.007 vs base 0.892 ± 0.006 (+0.002, inside the seed spread), seriousness severe recall 0.49 vs 0.56, gold-150 0.875 vs 0.899: **large does not win; the base stays** (`eval_results/c/classifier_large.json`). C2.4 done.
- [x] **C2.5 Student simplifier** (was B2.5b) · 💻 L + 🟠 G + 👤 A · S · Needs: CG2, C2.3b, gold-50 sheet
  Zero-shot bake-off; 4B bf16 LoRA on Colab; 8B variant; GGUF; E18–E20 + CPU seconds; model card.
  - [x] Zero-shot base (gold-50: 16/50 pass the product checks)
  - [x] 4B bf16 LoRA on Colab G4 + GGUF Q4_K_M (dev loss 0.353; gold-50 post-check pass 49/50, `eval_results/c/student_vs_base_gold50.json`)
  - [x] gold-50 blind sheet rated by Akshat (`sheet50` → `score50`): faithful yes base 0.84 / student 0.92 / teacher 0.98; plain English 3.00 / 4.64 / 4.80 (`eval_results/c/simplify_gold50.json`)
  - [x] 8B variant (`Qwen/Qwen3-8B`, `enable_thinking=False`; G4, 1 h 46 m, 16.4 units): dev loss 0.342 vs 0.353, but gold-50 post-checks 30/50 vs 49/50 (35 of 50 over 60 words, mean 68.7 words vs 43.2): **not adopted, the 4B stays the product model** (C-ADR-18, `eval_results/c/student_8b_vs_4b_gold50.json`)
- [ ] **C2.6 Novelty τ + E22** (was B2.2b) · 💻 L + 👤 A · S · Needs: C2.1, C1.4 window
- [ ] **C2.8 Risk-level thresholds + E17/E21 + E8r** (was B2.6b) · 💻 L · S · Needs: C2.4, C3.2, C1.4 window
  Wires `risklevel` to `reference_scores` + the window; thresholds fitted on train + dev only; E21 as the risk-points-only variant with the limitation stated.

**CG3:** classifier and student trained, evaluated, exported · τ and thresholds computed · extractor v2 trained and decided (kept only if it wins on dev). CG3 waits on the code lane too: C2.8 needs C3.2.

### C3 — Product on real data → gate CG4

- [ ] **C3.1 ★ Summary + financial extraction + E14** (was B1.3a-left + B1.3b) · 💻 L + 👤 A · **O** · Needs: C1.3, gold v3 verified for E14 (code can start before)
  - [x] C3.1a financial tables + financials stage (#224; dev coverage: all 11 values in 67 % of RHPs, cross-source agreement 257/258) · [x] C3.1b other red-flag inputs (#230) · [x] E14 final v1 (#236): NVM 0.682 (195 rows), status 0.667, page 0.766 on gold v3 (10 IPOs, verified by Akshat)
  - [ ] Follow-up (parse): *Summary of the Offer Document* missed in 16/55 dev RHPs; do it next to the heading-denylist task.
- [x] **C3.2 Red flags wired + E15** (was B1.4-left) · 💻 L · S · Needs: C3.1, gold v3 verified
  Includes rule-based flags (going concern, default / loan recall, SEBI/RBI/ED orders, fraud, qualified audit) that force the severe band regardless of the model.
  *Status:* merged (#233); E15 final v1 (#236): accuracy 0.646 on 130 rows, 0 serious disagreements. RF04/RF05 are low because the evaluator lacks the X-Ray offer facts (fix in C3.7).
- [ ] **C3.3 Trained models into the upload pipeline** · 💻 L · S · Needs: C2.4, C2.5, C2.6, C3.2
  Classifier ONNX, student GGUF (top 15 automatic, rest on click), novelty with τ, risk level → full report for any upload. Models load one stage at a time (16 GB RAM shared with Windows and Claude Code); measure RAM and seconds with `scripts/measure_memory.py`; try partial llama.cpp GPU offload on the 4 GB RTX 2050.
  *Latency plan (from C2.5, 12.3 s/risk on the laptop CPU ≈ 14 min per IPO of ~67 risks):* precompute simplifications for showcase / listed IPOs at ingest; for an upload simplify the top-N by seriousness up front and the rest lazily when the user expands a risk; batch / parallel requests to Ollama; measure GPU latency for the deployed version (C3.8 / C5.1). Not built yet.
- [ ] **C3.4 Compare on the rolling window** (was B3.2b) · 💻 L · S · Needs: C1.4, C3.1
  The Compare tab moves from its provisional data to the `splits.reference` rolling window.
- [ ] **C3.5 Newest-IPO showcase** · 💻 L + 👤 A · S · Needs: C3.3
  Build reports and X-Rays for the `demo` IPOs; add them to the library; record the demo cache; landing stats from real files. Akshat picks which IPOs lead the class demo.
- [ ] **C3.6 Report UI + Lab on the real API** (was B3.1b + B3.4b) · 💻 L · S · Needs: C3.3
  Mocks regenerated from real files by script; Lab sections for E13–E24 and the bench.
- [ ] **C3.7 Chat fixes** · 💻 L + 👤 A · S · Needs: CG0
  Investigate the 32 s `full`-profile latency; Akshat decides the "red flags in chat" guard question; E7 hand-check.
- [ ] **C3.8 Hardening sweep** (was B3.5b, local) · 💻 L · S · Needs: C3.6

**CG4:** upload any new RHP on the laptop → full report with trained models, red flags with pages, risk level with reasons + disclaimer; Playwright sweep green.

### C4 — FinSight Bench → gates CG5, CG6

- [ ] **C4.1 ★ Bench v1 build** · 💻 L + 👤 A · **O** · Needs: CG1 (and gold v3 for showcase IPOs)
  `bench/v1/` per C04 §2–5 (6 + 2 documents, input ladder with TOC page ranges, field map, pinned `redflags_version`, `frozen_files`); gold v4 pre-fill with the source hidden; Akshat verifies; freeze.
- [ ] **C4.3 Frontier runs** · 👤 A · Needs: C4.1 frozen (**not** any FinSight model)
  Opus and ChatGPT Go on every bench document + bench-dev; memory and web search off; plan, model string and timestamp recorded; consistency repeats (bench Task E).
- [ ] **C4.2 FinSight bench answers** · 💻 L · S · Needs: CG4, C4.1
- [ ] **C4.4 Scoring + blind rating + tables** · 💻 L + 👤 A · S · Needs: C4.2, C4.3

**CG5:** bench v1 scored with CIs; "where FinSight loses" list generated.

- [ ] **C4.5 Improvement loop + bench v2** · 💻 L · O for diagnosis, S for fixes · Needs: CG5
  Error analysis on bench-dev only; fixes with tests; FinSight re-run; v2 tables.
  - [ ] Qualifier / hedge-consistency check for the simplifier: compare original vs rewrite for added or dropped qualifiers ("soon", "all", "only", "no", an omitted court stay). C2.5 gold-50: all 4 of the student's "partly" rows were this kind; the number and certainty checks do not see them.

**CG6 = FEATURE FREEZE:** bench v2 done · all shipped features stable · nothing new after this, only fixes and docs.

### C5 — Finish

- [ ] **C5.1 Deploy** on the Google Cloud trial · per C08 · needs a budget alert and Akshat's "go"
- [ ] **C5.2 Docs and report results** · 💻 L · S — model cards, datasheets, report §7 from `eval_results/`, contribution claim from bench numbers, `10_FINSIGHT_EXPLAINED` sections for new code.
- [ ] **C5.3 Release tag** (v2.0.0) · 💻 L
- [ ] **C5.4 Report, slides, video, viva** · 👤 A

## 3. Dependency picture

```text
Data:     CG0 ─► C1.1 ─► C1.2 ─► C1.3 ─► C1.4 ═ CG1
GPU:      CG1 ─► C2.1 ─► C2.2 ─► C2.3 ═ CG2 ─► C2.4 (Kaggle) + C2.5 (Colab)
          C2.1 ─► C2.6          CG1 ─► C2.7 (Kaggle, parallel)
Code:     C1.3 ─► C3.1 ─► C3.2 ─► C2.8 (also needs C2.4)          ═ CG3 when C2.4, C2.5, C2.6, C2.8 are done
Product:  C2.4 + C2.5 + C2.6 + C3.2 ─► C3.3 ─► C3.5, C3.6 ─► C3.8 ═ CG4      (C3.7 any time after CG0)
Bench:    CG1 ─► C4.1 ─► C4.3 (Akshat)        CG4 + C4.1 ─► C4.2;   C4.2 + C4.3 ─► C4.4 ═ CG5 ─► C4.5 ═ CG6
```

## 4. Suggested first moves (in order, no dates)

1. Akshat: C06 §1 setup; drop `docs/phase3/` in the repo.
2. Code lane: C0.1 → C0.2 (Akshat runs the rate-check + vLLM smoke notebook).
3. Code lane: C1.1 → C1.2 → C1.3 → C1.4. While these run: Akshat verifies gold v3 (needed for C3.1/C3.2 and the bench).
4. As soon as CG1: GPU lane C2.1 → C2.2; Kaggle lane C2.7; code lane C3.1; Akshat lane C4.1 gold v4.
5. Bench frozen → Akshat does frontier runs while models train.

## 5. Scope

Full scope, nothing cut (Akshat's decision; it replaces the kickoff cuts of C-ADR-01). Restored: student 8B variant, BIR backfill (C1.5), classifier large, Compare on the rolling window (C3.4), bench consistency task (Task E), extractor v2 (C2.7), bench v2 (C4.5), sign-in, Hindi polish, deploy (C5.1). Bench documents stay 6 + 2 (C04 §2).

## 6. Critical path

**Ranked critical path** (each step needs the one before it; slack anywhere here moves the end):

C0.1 → C0.2 → C1.1 → C1.2 → C1.3 → C1.4 **[CG1]** → C2.1 → C2.2 → C2.3 **[CG2]** → C2.5 (4B) → C3.3 **[CG4]** → C4.2 → C4.4 **[CG5]**

**Parallel lanes after CG1:**

- **Bench lane (biggest time risk):** C4.1 (bench build, gold v4, TOC page ranges) → freeze → C4.3 frontier runs. It needs no FinSight model, so it starts at CG1.
- **Code lane:** C3.1 → C3.2 → C2.8; C3.6, C3.7, C3.8 when unblocked.
- **Kaggle lane:** C2.4 (TF-IDF + base) after CG2; C2.6 after C2.1.

**Akshat's hand-work per gate** (estimates; detail in C06 §2):

| Gate | Hours | What |
| --- | --- | --- |
| CG0 | ~1.5 | Setup + rate-check run |
| CG1 | ~2–3 | Approve the IPO list, manual downloads, confirm split counts |
| CG2 | ~3 | Segmentation check, bake-off rating + babysit, quality-100 + babysit |
| CG3 | ~2 | gold-150, gold-50, novelty pairs, Colab babysit |
| CG4 | ~2.5 | gold v3, chat guard decision + E7, demo pick |
| CG5 | ~19 | gold v4 + keys, TOC ranges, frontier runs, blind rating |
| CG6 | ~1 | Review the C4.5 diagnosis |
| **Total** | **~31** | Bench + gold v4 are about 60 % |
