# Add a red-flag check

A red-flag check turns one or two numbers the document discloses into OK, Watch, Concern, Not
available or Not applicable, with one plain sentence and the pages behind it. There are 13 (RF01–RF13).
Serious findings (going concern, regulator orders, qualified audit, default, fraud) are a separate
sentence-level scan in `src/finsight/redflags/severe.py`.

## Steps

1. **Describe the check** in `configs/redflags.yaml` under `checks`: `title` (shown on the card),
   `rule` (the "How this check works" text, plain English) and its thresholds as strings. Bump
   `version`: it is stored in every `redflags.json`, so old results stay explainable.
2. **Make sure the inputs exist.** Add the number to `RedFlagInputs` in
   `src/finsight/redflags/inputs.py` and fill it in both `inputs_from_summary` (the pipeline) and
   `inputs_from_gold` (gold v3 rows), so the status gold is computed by the same rule. `None` means
   "not found", never zero. If the number is not read yet, add it to the financial summary in
   `finsight.summary` first.
3. **Write the rule** in `src/finsight/redflags/rules.py` with the same signature as the others,
   `def rf14(x: RedFlagInputs, c: Mapping[str, Any], na: str) -> Result`, and add it to `CHECKS`.
   Return the evidence keys you used so the page chips work. A sentence with no approved wording goes
   into `DRAFT_SENTENCES`.
4. **Test it first** in `tests/redflags/test_redflag_rules.py`: one test per threshold edge (just
   below, at, just above), the missing case and, if it applies, the lender case. The forbidden-phrase
   test checks every sentence and rule text automatically.
5. **Bump `pipeline_version`** in `configs/config.yaml`: stored reports are then re-analysed when opened.
6. **Regenerate the docs:** `uv run poe docs-gen` rebuilds [Red-flag checks](../reference/redflags.md)
   and [Configuration files](../reference/configs.md) from the YAML.
7. **Check the risk level.** Each Watch adds 1 point and each Concern 2 (`configs/risklevel.yaml`), and
   the score is a share of the points possible, so a new check changes every score. Refit the
   thresholds on train + dev IPOs only (`scripts/score_reference_ipos.py`, C-ADR-25) before trusting
   the level again; never fit on test or bench IPOs (C-ADR-02).
8. **Measure.** Run E15 on dev while you work
   (`uv run python scripts/redflag_eval.py --slice dev --allow-unverified`). Run the final E15 on all
   slices once, and add gold statuses for the new check before reporting a number.
