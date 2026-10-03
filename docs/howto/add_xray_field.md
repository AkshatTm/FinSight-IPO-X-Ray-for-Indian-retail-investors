# Add a new X-Ray field

An X-Ray field is one fact on the fact sheet (for example the fresh issue size). Rules read it first; the fine-tuned QA model cross-checks it (ADR-018).

1. **Describe the field** in `configs/fields.yaml`:
   - `id`, `label_en`, `label_hi` (the Hindi is reviewed by Akshat);
   - `type`: `money`, `count`, `percent`, `range`, `text`, `list` or `table`;
   - `doc` (`rhp` or `prospectus`), `sections` to search (`cover` is the first pages);
   - `questions` (also used to ask the QA models);
   - `extractor` (`rules` or `table`), `fallback`;
   - `ladder: false` unless the field has weak labels and gold rows.
2. **Write the rule** in `src/finsight/extract/rules.py`: a function `def my_field(text: str) -> list[Hit]` that returns the raw text and the parsed value (use `finsight.normalize.parse_amount` for numbers, so lakh, crore, million and `[●]` are handled the same way everywhere). Add it to `RULES`.
3. **Test it first** in `tests/extract/test_rules.py` with short sentences in the style of real covers, including a placeholder `[●]` and a sentence that must not match.
4. **Gold rows:** add the field to the gold template so its accuracy can be measured. Never invent a gold value; leave it for Akshat to label.
5. **Rebuild** the X-Ray (`--stage rules`, then `--stage xray`) and check the page chip lands on the right box.
6. **Docs:** a new field changes the UI and the API reference. Regenerate `openapi.json` (`uv run poe gen-openapi`) if the API shape changed.
