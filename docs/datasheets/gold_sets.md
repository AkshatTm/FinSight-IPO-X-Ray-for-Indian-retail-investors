# Datasheet: gold sets

## Motivation

Scores mean something only against answers checked by a person on the document page. These files are small on purpose: one person checks every row.

## Composition

All in `data/gold/` (committed). Counts generated from the files:

<!-- generated:stats start -->

| File | Rows | IPOs | Label source |
| --- | --- | --- | --- |
| `gold_values.jsonl` | 110 | 10 | `ai_assisted_verified` 110 |
| `questions_dev.jsonl` | 50 | 3 | `ai_drafted_claude_chat` 20, `ai_drafted_claude_code` 30 |
| `questions_test.jsonl` | 67 | 7 | `ai_drafted_claude_chat` 67 |
| `weaklabel_audit.jsonl` | 50 | 46 | `ai_labelled_claude_chat_human_reviewed` 50 |
| `gold_v3_template.jsonl` | 270 | 10 | `none yet` 270 |

Questions (dev + test) by language: en 65, hi 40, hinglish 12; review status: pending 117. Advice-guard set: 120 questions (en 56, hi 30, hinglish 34), 0 reviewed by Akshat.

<!-- generated:stats end -->

- `gold_values.jsonl`: 11 fields of 10 recent IPOs, each with value, page and quote (Phase 1 X-Ray and extractor ladder).
- `questions_dev.jsonl`, `questions_test.jsonl`: chat questions with gold answers and evidence pages; some are unanswerable on purpose.
- `weaklabel_audit.jsonl`: the 50-row audit of the weak labels (E1).
- `advice_guard_set.csv`: advice and fact questions in English, Hindi and Hinglish (E8).
- `gold_v3_template.jsonl`: the Phase 2 red-flag inputs template, to be filled in a local session.
- The CSV sheets (`gold_verify_sheet.csv`, `hindi_fluency_sheet*.csv`, `asr_references.csv`) are the review sheets behind these files.

The [data formats reference](../reference/data_formats.md) lists every column.

## Labelling process (AI-assisted, disclosed)

Gold v1 values were pre-filled with AI help and then checked by Akshat against the PDF page (ADR-035); every row carries `label_source`. Chat questions were drafted with AI help and wait for Akshat's review (`review_status`, counted above). The advice-guard set was drafted with AI help and is not reviewed yet either; the guard results say so. One annotator, so no inter-annotator agreement is reported.

## Uses

Scoring only. Dev rows may be used to choose settings; test rows are used once per reported number. Gold IPOs are excluded from all training data.

## Distribution and licence

Values and short quotes from public offer documents, committed under the repository licence for evaluation. No personal data beyond names printed in the documents.

## Maintenance

Never edited to improve a score. Corrections are new commits with the reason in the message, and the affected results are re-run.
