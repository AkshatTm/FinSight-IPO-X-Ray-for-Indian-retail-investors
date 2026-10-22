# PROGRESS — ARGON (Phase 4)
<!-- ≤15 lines, overwrite each session. Newest state only. -->
Date: 2026-10-22
Done:
- AR-03 (L2 fixes): Blanked `severity_band_1_to_4`, sorted `actual_event` rows first (`train`->`dev`->`test`), added `rhp_page`/`quote_25w`, and added `BAND_AND_LABEL_GUIDE.md`.
- AR-08 (M3 code+nb): Wrote `ml/notebooks/m3_event_clf.ipynb` (T4 DEBUG + 3-seed G4 + ONNX `fp32` + `metrics.json`) and `ml/m3_event_clf/predict.py`.
- AR-04 (M1 data+nb): Wrote `ml/m1_student_v2/chat_sft_builder.py` (1,500 scripted near-miss unanswerables + `numkeep.py` filter + rewrite mixer) and `ml/notebooks/m1_teacher_gen.ipynb`.
In progress: Waiting for Akshat's L2 CSV verification and T4 `DEBUG=True` smoke runs on `m1_teacher_gen.ipynb` & `m3_event_clf.ipynb`.
Blocked:
- AR-02 (`expected.json` + `FORMAT_CATALOGUE.md`) paused awaiting CC's word-box export in `docs/phase4/comms/to_argon.md`.
- AR-05 (L3 Gold v4) awaiting `data/platform_bench/FinSight_Platform_Bench.xlsx` (Akshat/CC-03).
Next (Akshat): Verify `akshat_verification_gold.csv` (~60 min); run T4 `DEBUG=True` on `m1_teacher_gen.ipynb` (~4 min, ~0.10 units) & `m3_event_clf.ipynb` (~3 min, ~0.08 units).
Colab units used so far: 0 / 140
