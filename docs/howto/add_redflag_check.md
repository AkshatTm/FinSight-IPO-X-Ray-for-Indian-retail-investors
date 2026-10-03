# Add a red-flag check

A red-flag check turns one or two numbers from the financial summary into OK / Watch / Concern / Not available / Not applicable, with one plain sentence and the pages behind it (B01 §5). The scope is fixed at 13 checks (B01); a new check needs Akshat's approval first.

1. **Describe the check** in `configs/redflags.yaml`: `title` (from B05 §5.4, verbatim), `rule` (the "How this check works" text, in plain English) and its thresholds as strings. Bump `version`: it is stored in every `redflags.json`, so old results stay explainable.
2. **Make sure the inputs exist.** Add the number to `RedFlagInputs` in `src/finsight/redflags/inputs.py` and read it in both `inputs_from_summary` (the pipeline) and `inputs_from_gold` (the gold v3 rows), so the status gold is computed by the same rule. `None` always means "not found", never zero.
3. **Write the rule** in `src/finsight/redflags/rules.py`: `def rfNN(x, spec, missing) -> Result`. Use the sentence templates from B05 §5.4 word for word; a sentence B05 doesn't have goes into `DRAFT_SENTENCES` and the copy-approval list in `docs/AKSHAT_TODO.md`. Return the evidence keys you used so the page chips work.
4. **Test it first** in `tests/redflags/test_redflag_rules.py`: one test per threshold edge (just below, at, just above), the missing case and, if it applies, the lender case. The forbidden-phrase test there checks every sentence and rule text automatically.
5. **Regenerate the docs** (`uv run poe docs-gen`): the [red-flag reference](../reference/redflags.md) is built from the YAML.
6. **Risk level:** each Watch adds 1 point and each Concern 2 (`configs/risklevel.yaml`); the level is normalised by the checks that could run, so a new check changes the reference quantiles. Re-run the local quantile job (B2.6b) before trusting the level again.
