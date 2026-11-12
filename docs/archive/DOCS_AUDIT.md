# Documentation audit (v1.1, docs/v1.1 branch)

Audit of every Markdown file in the repository and of the `mkdocs.yml` nav, done before the v1.1
documentation rewrite. The table at the end is generated (stale-term counts are a case-insensitive
search); the decisions and findings were made by reading the files.

## Decisions

- **keep**: correct as is, or a historical record that must not change (planning docs, gate
  evidence, course report drafts). Planning docs stay at their paths because `CLAUDE.md`,
  `AGENTS.md`, `scripts/docs_gen.py` and the code link to them; each gets a one-line
  "historical record" banner and is left out of the docs site, which links to it on GitHub.
- **update**: rewritten or edited to match the code at v1.1.
- **merge**: content moved into a new site page; the old file is archived.
- **archive**: moved to `docs/archive/` with a one-line note on top. Nothing is deleted.

## Stale facts found

| Stale fact | Where | Truth at v1.1 (source) |
| --- | --- | --- |
| Chat in English **or Hindi**, voice input, faster-whisper, `--group asr` | README, docs/index.md, RUN_LOCALLY.md, PRODUCT.md, how-tos, guard card, report drafts | English-only; Hindi + voice removed 3 Nov (CHANGELOG `[1.1]`, commits `fb1b871`, `ecc0436`) |
| "Phase 2 thresholds … provisional placeholders" | README Limitations | thresholds fitted on 165 train+dev IPOs, `provisional: false` (C-ADR-25, `configs/risklevel.yaml`) |
| Results table = Phase 1 ladder/E7 only | README | headline numbers are `eval_results/final/FINAL_SCORECARD.md` |
| Chat model `qwen3.5:2b` (profile `full`) | README, tutorials, troubleshooting | the app runs profile `local`: `finsight-student:q4` through Ollama (`start.bat`, `configs/config.yaml`) |
| `uv run poe app`, Ctrl+C to stop; start.bat does `git pull` on main | RUN_LOCALLY.md | `start.bat` menu (start/stop/restart/status), minimised windows, `stop.bat` (commit `ea702fa`, `fa193f7`) |
| "Upload pipeline only validates the file; later stages added part by part" | tutorials/first_document.md | 14 stages from `validated` to `index`, after the `received` event (`src/finsight/jobs/pipeline.py`, `model_stages.py`) |
| "This site is the B4.1 skeleton … added Mon 26 Oct" | docs/index.md | finished |
| Classifier "ONNX int8" | model_cards/index.md, howto/retrain_classifier.md | ONNX **fp32** shipped; int8 rejected (`eval_results/c/classifier_onnx_int8_attempt.json`) |
| Simplifier trained on Kaggle (QLoRA), served by vLLM on an L4 | howto/retrain_simplifier.md | LoRA on a Colab G4, GGUF Q4_K_M in Ollama (model card, `student_train_metrics.json`) |
| Cloud Run, Secret Manager, Supabase, Vercel runbooks | runbooks/*, HOSTING_SETUP_STEPS.md, DEPLOY_STEPS.md, SECURITY.md | nothing was deployed; local only (B-ADR-16); deploy cut with Phase 4 |
| "riskier than X % of past IPOs" percentile | B05/B06 specs, 10_FINSIGHT_EXPLAINED | hidden (`null` + note), C-ADR-28 |
| Severe finding about promoter forces High | B-docs | only issuer events force High (C-ADR-26) |
| ADR index Phase 3 table empty | docs/adr/index.md | `docs_gen.py` matched only `###` headings; C_DECISIONS uses `##` (fixed) |
| No Phase 4 decision/plan status | everywhere | Phase 4 closed: Platform Bench, M1–M5, gold v4, CC-07/09/10 cut (PROGRESS.md) |
| CHANGELOG has no `[1.0]`; `[Unreleased]` = final | CHANGELOG.md | tags `v1.0`, `v1.1-pre` exist; v1.1 released from this branch |
| `docs/final/CLEANUP.md` | asked for in the brief | **does not exist** on any branch; the HF repo `AkshatTm/finsight-weights-archive` README refers to it and held only that README (checked 7 Nov). **Update 12 Nov:** CLEANUP.md was added in `9d80aa1` and the archive now holds the weights; the operations page links both |
| Dead links reported only as INFO | mkdocs.yml `validation: not_found: info` | site pages now fail the strict build on a dead link; `scripts/check_links.py` checks every Markdown file |
| `docs/screenshots/` excluded from the site | mkdocs.yml | `screenshots/final/` is published so the user guide can show it |

## mkdocs.yml nav (before)

Home · Tutorials (2) · How-to guides (7) · Reference (10, incl. B06 contract) · Explanation (9, incl.
Phase 1/2 architecture design docs) · Models and data (12) · Operations (3, all cloud) · Phase 3 (10
planning docs) · Project (9). Planning docs were presented next to current reference pages with no
marker; three of the four "Operations" pages describe hosting that never existed.

## mkdocs.yml nav (after)

Getting started · User guide · Architecture · Data · Models · Evaluation · API reference ·
Configuration · Development · Operations · Decisions · Project history · Glossary · FAQ.

## Every Markdown file

| File | Lines | Decision | Stale terms (count) | Note |
| --- | --- | --- | --- | --- |
| `.github/pull_request_template.md` | 18 | update | — | PR template; issue templates added |
| `AGENTS.md` | 42 | update | — | current-state lines only |
| `CHANGELOG.md` | 67 | update | Hindi 4, voice/ASR 9, cloud 8 | v1.0 and v1.1 entries |
| `CLAUDE.md` | 85 | update | voice/ASR 2, cloud 4 | current-state lines only |
| `CODE_OF_CONDUCT.md` | 9 | update | — | Contributor Covenant reference |
| `CONTRIBUTING.md` | 49 | update | — | current commands and branch rules |
| `DESIGN.md` | 15 | keep | — | design-skill brief |
| `PRIVACY.md` | 35 | update | — | what is stored, where, how to delete |
| `PRODUCT.md` | 13 | keep | Hindi 2, voice/ASR 1 | design-skill brief (Hindi line noted, not product truth) |
| `PROGRESS.md` | 39 | keep | Hindi 2, voice/ASR 1 | session log; resume note points at docs/v1.1 |
| `README.md` | 117 | update | Hindi 4, voice/ASR 2, old LLM 1 | rewritten as the front page (v1.1) |
| `SECURITY.md` | 29 | update | cloud 3 | local-only threat model; cloud secrets removed |
| `deploy/space/README.md` | 17 | keep | — | dormant Space README (never deployed) |
| `docs/00_README.md` | 56 | keep | Hindi 1, voice/ASR 1 | Phase 1 planning record; banner added |
| `docs/01_PRD.md` | 244 | keep | Hindi 12, voice/ASR 7 | Phase 1 planning record; banner added |
| `docs/02_ARCHITECTURE.md` | 394 | keep | voice/ASR 13, cloud 1, old LLM 2 | Phase 1 planning record; banner added |
| `docs/03_UI_UX_DESIGN.md` | 310 | keep | Hindi 11, voice/ASR 4 | Phase 1 planning record; banner added |
| `docs/04_TECH_STACK_AND_RESOURCES.md` | 173 | keep | Hindi 6, voice/ASR 8, cloud 2, old LLM 2 | Phase 1 planning record; banner added |
| `docs/05_DATA_AND_EVALUATION.md` | 218 | keep | Hindi 7, voice/ASR 7 | Phase 1 planning record; banner added |
| `docs/06_API_CONTRACT.md` | 150 | keep | voice/ASR 6, cloud 1, old LLM 1 | Phase 1 planning record; banner added |
| `docs/07_ROADMAP.md` | 278 | keep | Hindi 15, voice/ASR 15, cloud 2 | Phase 1 planning record; banner added |
| `docs/08_GIT_WORKFLOW.md` | 123 | keep | voice/ASR 2, TODO 1 | Phase 1 planning record; banner added |
| `docs/09_DECISIONS.md` | 406 | keep | Hindi 62, voice/ASR 15, cloud 10, old LLM 11 | Phase 1 planning record; banner added |
| `docs/10_FINSIGHT_EXPLAINED.md` | 858 | keep | Hindi 26, voice/ASR 17, cloud 12 | Phase 1 planning record; banner added |
| `docs/11_CLAUDE_CODE_PROMPTS.md` | 73 | keep | — | Phase 1 planning record; banner added |
| `docs/12_FRONTEND_SPEC.md` | 767 | keep | Hindi 22, voice/ASR 11 | Phase 1 planning record; banner added |
| `docs/AKSHAT_TODO.md` | 278 | keep | Hindi 31, voice/ASR 7, cloud 8, old LLM 1 | owner to-do list (history); banner added |
| `docs/DEPLOY_STEPS.md` | 82 | archive | voice/ASR 2, cloud 6 | cloud deploy never happened (B-ADR-16, Phase 4 cut) |
| `docs/EXECUTION_PLAN.md` | 261 | keep | Hindi 12, voice/ASR 18, cloud 2 | Phase 1 plan; banner added |
| `docs/MORNING_REPORT.md` | 149 | archive | Hindi 3, voice/ASR 1, cloud 9 | one-off session report |
| `docs/PROGRESS_PHASE1.md` | 34 | keep | Hindi 15, voice/ASR 12, old LLM 5 | phase log; banner added |
| `docs/PROGRESS_PHASE2.md` | 26 | keep | Hindi 1, cloud 4 | phase log; banner added |
| `docs/RUN_LOCALLY.md` | 115 | archive | Hindi 3, voice/ASR 3 | superseded by getting-started/ (Hindi, voice, git-pull start.bat) |
| `docs/RUN_LOCALLY_TIMINGS.md` | 31 | archive | — | Seshaasai smoke run; final timings are in FINAL_SCORECARD |
| `docs/adr/index.md` | 123 | update | Hindi 2, voice/ASR 2, cloud 5 | generated; Phase 3 table was empty (regex bug), Phase 4 added |
| `docs/architecture/index.md` | 160 | update | cloud 3 | system overview for v1.1 |
| `docs/datasheets/corpus.md` | 45 | update | — | status lines; generated blocks kept |
| `docs/datasheets/gold_sets.md` | 48 | update | Hindi 5 | status lines; generated blocks kept |
| `docs/datasheets/index.md` | 14 | update | — | status lines; generated blocks kept |
| `docs/datasheets/new_ipos.md` | 33 | update | — | status lines; generated blocks kept |
| `docs/datasheets/risk_bank.md` | 31 | update | — | status lines; generated blocks kept |
| `docs/datasheets/weak_labels.md` | 49 | update | — | status lines; generated blocks kept |
| `docs/evaluation.md` | 83 | update | voice/ASR 2 | final scorecard section added; generated blocks kept |
| `docs/final/CONTRACT.md` | 143 | keep | voice/ASR 2 | final-session rules and API contract (history) |
| `docs/final/RULES.md` | 25 | keep | Hindi 1, voice/ASR 1 | final-session rules and API contract (history) |
| `docs/gates/BG0.md` | 15 | keep | cloud 2 | gate evidence (history) |
| `docs/gates/G3.md` | 27 | keep | Hindi 7, voice/ASR 8, old LLM 1 | gate evidence (history) |
| `docs/gates/G4.md` | 18 | keep | Hindi 1, voice/ASR 6, old LLM 2 | gate evidence (history) |
| `docs/glossary.md` | 57 | keep | Hindi 1 | generated from configs/glossary*.yaml |
| `docs/howto/add_redflag_check.md` | 10 | merge | — | into development/add-redflag-check.md |
| `docs/howto/add_showcase_ipo.md` | 13 | merge | — | into operations/index.md (showcase + preload) |
| `docs/howto/add_xray_field.md` | 16 | merge | Hindi 1 | into development/index.md (label_hi still in fields.yaml) |
| `docs/howto/record_demo_cache.md` | 17 | archive | Hindi 1 | demo cache uses Hindi questions and the old qwen3.5 profile |
| `docs/howto/retrain_classifier.md` | 27 | archive | — | says ONNX int8 on a CPU worker (shipped: fp32, laptop); recipe now in the model card |
| `docs/howto/retrain_simplifier.md` | 14 | archive | — | says Kaggle QLoRA + vLLM/L4 (real run: Colab G4 LoRA); recipe now in the model card |
| `docs/index.md` | 27 | update | Hindi 1 | rewritten home page |
| `docs/model_cards/bilstm_crf.md` | 76 | update | — | HF card metadata, product status, rejected variants |
| `docs/model_cards/extractor_qa.md` | 103 | update | — | HF card metadata, product status, rejected variants |
| `docs/model_cards/guard_muril.md` | 50 | update | Hindi 3 | HF card metadata, product status, rejected variants |
| `docs/model_cards/index.md` | 13 | update | — | HF card metadata, product status, rejected variants |
| `docs/model_cards/risk_classifier.md` | 48 | update | — | HF card metadata, product status, rejected variants |
| `docs/model_cards/risk_simplifier.md` | 67 | update | — | HF card metadata, product status, rejected variants |
| `docs/phase2/B00_README.md` | 45 | keep | Hindi 1, voice/ASR 1, cloud 6 | planning record; banner added, linked from History |
| `docs/phase2/B01_PRD.md` | 154 | keep | Hindi 2, voice/ASR 1, cloud 5 | planning record; banner added, linked from History |
| `docs/phase2/B02_ARCHITECTURE.md` | 276 | keep | voice/ASR 1, cloud 24, old LLM 2 | planning record; banner added, linked from History |
| `docs/phase2/B03_MODELS_AND_TRAINING.md` | 108 | keep | cloud 3, old LLM 3 | planning record; banner added, linked from History |
| `docs/phase2/B04_DATA_AND_EVALUATION.md` | 55 | keep | cloud 1 | planning record; banner added, linked from History |
| `docs/phase2/B05_UI_SPEC.md` | 224 | keep | Hindi 1 | planning record; banner added, linked from History |
| `docs/phase2/B06_API_CONTRACT.md` | 128 | keep | cloud 1 | planning record; banner added, linked from History |
| `docs/phase2/B07_ROADMAP.md` | 168 | keep | Hindi 2, voice/ASR 2, cloud 12 | planning record; banner added, linked from History |
| `docs/phase2/B08_DECISIONS.md` | 79 | keep | cloud 12 | planning record; banner added, linked from History |
| `docs/phase2/B09_DOCUMENTATION_STANDARDS.md` | 122 | keep | cloud 1 | planning record; banner added, linked from History |
| `docs/phase2/B10_PROMPTS.md` | 109 | keep | voice/ASR 1, cloud 1 | planning record; banner added, linked from History |
| `docs/phase2/B_EXECUTION_PLAN.md` | 341 | keep | Hindi 3, voice/ASR 1, cloud 25, old LLM 1 | planning record; banner added, linked from History |
| `docs/phase2/COLAB_STEPS_student.md` | 12 | keep | — | planning record; banner added, linked from History |
| `docs/phase2/COLAB_STEPS_teacher.md` | 14 | keep | — | planning record; banner added, linked from History |
| `docs/phase2/HOSTING_SETUP_STEPS.md` | 65 | archive | cloud 16 | cloud hosting steps (B-ADR-16) |
| `docs/phase2/datasheets/teacher_outputs.md` | 53 | keep | — | generated teacher datasheet |
| `docs/phase3/C00_README.md` | 86 | keep | Hindi 1, voice/ASR 2 | planning record; banner added, linked from History |
| `docs/phase3/C01_STRATEGY.md` | 68 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/C02_DATA.md` | 94 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/C03_TRAINING.md` | 126 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/C04_BENCHMARK.md` | 107 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/C05_ROADMAP.md` | 195 | keep | Hindi 1 | planning record; banner added, linked from History |
| `docs/phase3/C06_AKSHAT_CHECKLIST.md` | 51 | keep | Hindi 1, voice/ASR 1 | planning record; banner added, linked from History |
| `docs/phase3/C07_PROMPTS.md` | 104 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/C08_DEPLOY.md` | 34 | keep | cloud 4 | planning record; banner added, linked from History |
| `docs/phase3/C09_DOCS_AUTHORITY.md` | 34 | keep | cloud 2 | planning record; banner added, linked from History |
| `docs/phase3/C3_1_PLAN.md` | 42 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_bench_teacher.md` | 26 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_gold_eval.md` | 15 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_rate_check.md` | 18 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_student.md` | 24 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_student_8b.md` | 22 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_teacher_bakeoff.md` | 26 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_teacher_full.md` | 27 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/COLAB_STEPS_template.md` | 25 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/C_DECISIONS.md` | 169 | keep | Hindi 2 | planning record; banner added, linked from History |
| `docs/phase3/C_EXECUTION_PLAN.md` | 254 | keep | voice/ASR 1 | planning record; banner added, linked from History |
| `docs/phase3/KAGGLE_STEPS_classifier.md` | 40 | keep | — | planning record; banner added, linked from History |
| `docs/phase3/bench_error_analysis.md` | 50 | keep | — | generated bench failures |
| `docs/phase4/CC05A_JIO_DIAGNOSIS.md` | 45 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/KICKSTART_ARGON.md` | 32 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/KICKSTART_CC.md` | 33 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/P4_EXECUTION_PLAN_ARGON.md` | 106 | keep | Hindi 1 | planning record; banner added, linked from History |
| `docs/phase4/P4_EXECUTION_PLAN_CC.md` | 84 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/P4_GIT_WORKFLOW.md` | 58 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/P4_HANDOFF_CONTRACT.md` | 120 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/P4_MODEL_SPECS.md` | 95 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/P4_PLAN.md` | 108 | keep | Hindi 1 | planning record; banner added, linked from History |
| `docs/phase4/P4_PRODUCT_SPECS.md` | 75 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/PROGRESS_ARGON.md` | 13 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/PROGRESS_CC.md` | 11 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/PROMPTS.md` | 176 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/README.md` | 17 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/comms/to_argon.md` | 58 | keep | — | planning record; banner added, linked from History |
| `docs/phase4/comms/to_cc.md` | 38 | keep | — | planning record; banner added, linked from History |
| `docs/reference/api.md` | 9 | keep | — | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/reference/cli.md` | 32 | keep | — | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/reference/compare.md` | 22 | keep | — | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/reference/config.md` | 139 | keep | old LLM 3 | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/reference/data_formats.md` | 248 | keep | Hindi 3 | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/reference/python.md` | 45 | keep | — | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/reference/redflags.md` | 23 | keep | — | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/reference/risklevel.md` | 43 | keep | — | generated by scripts/docs_gen.py (api.md hand-written: updated) |
| `docs/runbooks/RESTORE_DB.md` | 55 | archive | cloud 3 | Supabase/Secret Manager runbooks for hosting that never existed |
| `docs/runbooks/ROTATE_SECRETS.md` | 58 | archive | cloud 10 | Supabase/Secret Manager runbooks for hosting that never existed |
| `docs/security_review.md` | 37 | keep | cloud 6 | B3.5a review record; listed under history |
| `docs/templates/frontend.CLAUDE.md` | 28 | keep | Hindi 2 | template, not published |
| `docs/troubleshooting.md` | 86 | update | cloud 2, old LLM 2 | moved to getting-started/troubleshooting.md |
| `docs/tutorials/first_document.md` | 48 | archive | — | replaced by getting-started/ (dev_light, mock-only upload note) |
| `docs/tutorials/run_locally.md` | 61 | archive | old LLM 1 | replaced by getting-started/ (dev_light, mock-only upload note) |
| `eval_results/final/FINAL_SCORECARD.md` | 104 | keep | Hindi 1, voice/ASR 1 | result file (source of truth) |
| `frontend/AGENTS.md` | 9 | keep | — | frontend README / agent notes |
| `frontend/CLAUDE.md` | 28 | keep | Hindi 2 | frontend README / agent notes |
| `frontend/README.md` | 50 | keep | cloud 1 | frontend README / agent notes |
| `report/03_related_work.md` | 41 | keep | Hindi 3, voice/ASR 3 | course report drafts for v1.0 (describe Hindi + voice as built then) |
| `report/04_data.md` | 71 | keep | Hindi 1, voice/ASR 1 | course report drafts for v1.0 (describe Hindi + voice as built then) |
| `report/05_preprocessing.md` | 52 | keep | Hindi 3, voice/ASR 1 | course report drafts for v1.0 (describe Hindi + voice as built then) |
| `report/06_method.md` | 119 | keep | Hindi 3, voice/ASR 3, old LLM 1 | course report drafts for v1.0 (describe Hindi + voice as built then) |
| `report/07_results.md` | 191 | keep | Hindi 7, voice/ASR 2, cloud 1, old LLM 4, TODO 1 | course report drafts for v1.0 (describe Hindi + voice as built then) |
| `report/08_error_analysis.md` | 62 | keep | Hindi 12, voice/ASR 1, old LLM 1 | course report drafts for v1.0 (describe Hindi + voice as built then) |
| `report/11_reproducibility.md` | 46 | keep | voice/ASR 2 | course report drafts for v1.0 (describe Hindi + voice as built then) |
| `report/README.md` | 56 | keep | Hindi 1, voice/ASR 2 | course report drafts for v1.0 (describe Hindi + voice as built then) |

## Later moves (12 Nov 2026)

- `DESIGN.md` → `docs/archive/DESIGN_seed.md` and `PRODUCT.md` → `docs/archive/PRODUCT_seed.md`: design-skill seed files from Phase 1 (old palette, Hindi chat); no live page links them.
