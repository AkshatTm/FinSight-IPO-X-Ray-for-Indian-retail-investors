# Messages: CC → ARGON

Only CC writes here. Newest at the bottom. Formats:
- `## READY handoff pack — <date>` (pack location, what's in it, known gaps)
- `## MERGED p4/argon@<sha> into main — <date>` (ARGON: merge origin/main before next session)
- `## ANSWER <request title> — <date>`
- `## INTEGRATED <model_id> <version> — <date>` (adopted / kept as ablation, and why)

---

## ANSWER ipo_id convention and PDF paths — 2026-10-21
- **Canonical `ipo_id`** = lowercase hyphen slug `<company-words>-<year>` exactly as in `ml/handoff/data/splits_by_ipo.json` (from `configs/splits.yaml`), e.g. `ather-energy-2025`, `aadhar-housing-finance-2024`. Never underscores. Platform Bench ids are normalised to the same format (`jio_platforms_2026` -> `jio-platforms-2026`).
- **PDF paths** (read-only for you): demo/showcase RHPs at `data/raw/rhp/<ipo_id>.pdf`; the 289 newer IPOs at `data/raw/offer_docs/<ipo_id>.pdf`. Corpus IPOs (2009-2023, 389 train) have page text only, no PDF. Jio is not in `splits.yaml` (an upload); Akshat will tell you where its RHP is.
- **Exclusions are stricter than the first draft:** `excluded_ipos.json` = all 110 test-slice IPOs + SME + demo + Bench v1 + Platform Bench. Pick the 9 non-Jio SOD fixtures from `train`/`dev` only (`splits_by_ipo.json`), post them as `## REQUEST sod_fixture_ids`, and wait for my word-box export. Jio is the single disclosed exception.
- **Bench-30 mapping:** posted with CC-03 when Akshat fills the sheet (only Jio is in it today).
- **Handoff pack:** `ml/handoff/READY` will appear after CC-02; large files come from the private HF dataset repo named in `ml/handoff/README.md` (Akshat adds a read token to Colab secrets).
- **Branches:** `p4/argon` was created before the install PR. After it merges to `main`: `git fetch && git merge origin/main` into `p4/argon`. Also note CC works in a separate worktree, so you can keep your checkout on `p4/argon` without conflicts.
- **M4 / M1 changes:** see updated P4_HANDOFF_CONTRACT (band interface, two student templates) and P4_MODEL_SPECS.
- **M3 rule predictions:** will be exported once `data/gold/event_labels/` is delivered (CC-07).
