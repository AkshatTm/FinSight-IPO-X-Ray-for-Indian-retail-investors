# PROGRESS (newest first; "Resume here" on top; ≤ 10 log lines; Phase 2 log: docs/PROGRESS_PHASE2.md, Phase 1: docs/PROGRESS_PHASE1.md)

## Resume here
- **Phase:** final session (v1.1). Phase 4 is **closed**: no model was trained, so CC-03/CC-10 (Platform Bench), CC-09 (model integration), M1–M5, gold v4 and CC-07 were cut; the product keeps the Phase 3 models. Unfinished CC-07 price-band schema work is on `origin/p4/cc` (not needed: `PriceBand` already lives in `summary/sod.py`).
- **Released:** v1.1 on `main` (tag `v1.1`, GitHub Release). Docs rewritten on `docs/v1.1`: README, docs site (`uv run poe docs-build`), model cards, CHANGELOG, policies, issue templates, CITATION.cff; audit in `docs/archive/DOCS_AUDIT.md`.
- **Branch history:** `final` (tag `v1.1-pre` = main before it), then `docs/v1.1`. Rules for the two sessions: `docs/final/RULES.md`; API shape for the frontend: `docs/final/CONTRACT.md`.
- **Done on `final`:** report serves `sod`; C-ADR-26 (only issuer events force High; Jio High → Low); C-ADR-28 (percentile hidden, length bias); Compare names the issuer; pipeline_version 4.2; Hindi + voice removed (English-only API, stray `lang` ignored); stale/blank analyses purged (backup `data/backup_2026-11-03/`); `scripts/preload.py`.
- **Numbers:** `eval_results/final/FINAL_SCORECARD.md` (E14 0.774 / E15 0.769 re-measured; the rest carried and marked).
- **Leftovers:** Hindi prompt code in `generate/` and eval scripts is unreachable but not deleted; refit of the risk-level reference normalised by risk-factor count; C-ADR-26 does not judge materiality or "set aside"; showcase reports need `scripts/build_showcase.py`.
- **Next:** none planned. Open questions for Akshat: make the HF dataset `AkshatTm/finsight-gpu-jobs` private if that was not intended; the scorecard's "2021–2026" universe label (the CSV says 2024–2026).
- **Open files / failing tests:** none (fast suite green).

## Log
- Docs v1.1: README, 14-section docs site (strict build), HF-format model cards, verified API guide, CHANGELOG / CONTRIBUTING / SECURITY / PRIVACY / NOTICE / CITATION, stale pages archived; merged with the `final` branch into main.
- Final session: Phase 4 closed (no trained model); `final` branch with sod in the report, C-ADR-26/28, English-only API, purge + preload, final scorecard.
- C2.8 fit done (E21 open): `score_reference_ipos.py` scored 440 train+dev IPOs (classifier seed 42 on the laptop GPU, ~10 min after 25 min classification); thresholds 0.2857 / 0.4167 from 165 full documents, `provisional: false` (C-ADR-25). E21 waits for `data/gold/outcomes.csv`; points-only scores saturate (43 % at 1.0). No Colab units used.
- BIR backfill 48 links -> 40 files: files are named by `mapping_key` and a second live PDF in the same row is skipped (11 rows have 2+ direct PDF links).
- C3.7/C3.7b/C3.4 done: E14 v2 NVM 0.769 (v1 0.682 frozen), E15 v2 0.762 (v1 0.646; wiring alone 0.731); stale sections.json was the main cause; retrieval 32 s not reproduced (9.6 s, CPU reranker 26-45 s); Compare reference n=40 issue size only (provisional); upload pipeline gains facts + compare stages (#239 #240 #241).
- C2.6 closed: 60 pairs rated, tau 0.71, precision 0.911 on 45 pairs (C-ADR-14, merged in #219).
- C2.7 done: extractor v2 trained on Kaggle (3 seeds, weak labels v3 incl. 2024+ cover seeds, no manual labels). Dev F1 0.974 vs v1 0.949 (52 unseen IPOs, rule-derived labels); gold ladder full NVM dev 0.639 vs 0.611, test 0.696 vs 0.738 (reporting row, test-informed). Kept as `models/extractor_v2/`; product default unchanged. v1 kept as the product extractor, v2 is a reported ablation (decided, #242). Details: `docs/model_cards/extractor_qa.md`.
- C3.2 merged (#233); gold v3 verified by Akshat; E14/E15 final v1 (#236): E14 NVM 0.682 (195 rows), status 0.667, page 0.766; E15 acc 0.646 (130), 0 serious disagreements. RF04/RF05 low = evaluator lacks X-Ray offer facts (fix in C3.7).
- C2.4 done: large (DeBERTa-v3-large, 3 seeds, Colab G4) 0.894 vs base 0.892 on dev, inside the seed spread, lower severe recall; the base stays the classifier; ONNX fp32 is the shipped export
- C2.5 8B variant done and not adopted: gold-50 post-checks 30/50 vs the 4B's 49/50 (outputs too long, 68.7 vs 43.2 words) despite dev loss 0.342 vs 0.353; 16.4 units; serving format checked (raw training format gives the same lengths); the 4B stays the product model (C-ADR-18)
- C2.4 base done: 3 seeds on Kaggle, dev macro-F1 0.892 ± 0.006 vs TF-IDF 0.862, gold-150 0.899; seriousness MAE 0.186 / severe recall 0.56 (dev); ONNX fp32 exact (int8 rejected); large on Colab pending
- C1.5 done: BIR link check (`scripts/check_bir_links.py`): 855 links, 48 direct PDFs live, 780 HTML pages, 27 dead; backfill decision in AKSHAT_TODO
- C3.1a: summary financial tables + financials stage (PR #224); dev coverage: all 11 values in 67% of RHPs, cross-source agreement 257/258.
- C2.5 done (4B): gold-50 human rating: faithful yes base 0.84 / student 0.92 (CI 0.81-0.97) / teacher 0.98, plain English 3.00 / 4.64 / 4.80; post-check rejects cut-off outputs now (base had 9; student and teacher 0)
- C2.5 follow-ups: notebook GGUF fix + test, `train_runtime_s` 4,224 s recorded, model card, E19/E20 + CPU timing (12.3 s per risk, 60 dev risks; FKGL 19.0 -> 9.6; 3/60 rejected), 8B preset + steps ready, gold-50 sheet written
- C2.5 done (4B): student LoRA trained on the G4 (dev loss 0.353, gold-50 post-check 49/50 vs base 16/50), GGUF built; human gold-50 rating, E18-E20, 8B and model card still open
- C2.3b done: `teacher_cleanup` (strict numbers, category remap v1, non-risk titles, severe band); teacher prompt v1.1 tie-break rules; student notebook `RESUME` flag + per-epoch checkpoint
- **CG2 passed** (C2.3): quality-100 rated, faithful 98 % | category_correct 94 % | notes 17 (`data/processed/teacher/quality_sheet.csv` + `quality_ratings.csv`, committed); no teacher rerun. Follow-ups → C2.3b (strict number filter, category remap, title check, severe band). Roadmap back to full scope (no cut line); C1.2/C1.3 ticked.
- C2.3 teacher run: Gemma-4-31B-it on the G4, 12,000 risks in 44.7 min, 10,892 kept; quality-100 sheet written; gold_eval (gold-150 pre-fill + gold-50 teacher) done; G4 released
- C2.2 done: Gemma-4-31B-it wins the blind bake-off (faithful yes 0.98 vs 0.90 / 0.88), C-ADR-05; C0.2 done: vLLM 0.31.0 pin, G4 tier (CG0 passed)
- Colab lane automated: HF job repo IO, `scripts/gpu_jobs.py`, presets, GPU auto-config, auto-disconnect (C-ADR-13 accepted); colab-mcp installed locally
- C2.1 done: bank 29,677 rows (440 IPOs), eval 8,819 (110 test IPOs), teacher input 12,305 achievable at cap 35, 12,000 written; E13b hand-checked (73/75 boundaries)
- C1.4 done: splits frozen (`configs/splits.yaml`, `data/manifests/`), leakage tests green; CG0 setup check passed (HF, Kaggle via `uvx kaggle`, disk)
- C1.2/C1.3 done: 289 docs fetched, 275 parsed, 14 excluded (12 SME, 2 unnumbered risks); section-header dash fix
- C1.3 fix: Risk Factors missed by 6 batch docs (wrapped TOC leaders, unmapped glyphs, singular title, heading fallback); regression tests; all 6 now parse
- C2.8 code: rolling-window reference scores, tercile fit on train+dev, E21 outcomes module with import guard; fit and E21 runs in AKSHAT_TODO
- C2.6 code: novelty tau rule, blind pair sheet, scoring; rating in AKSHAT_TODO
- Blockers: none.
