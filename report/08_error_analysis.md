# 8 Error analysis

> **DRAFT — Akshat to rewrite in his voice.** Ten real failures, each read from a committed result file
> (paths given). Causes marked *likely* were not investigated further and must be checked before the
> report states them as fact.

All extractor rows are test IPOs, full-document setting, from `eval_results/ladder/`.

| # | Where | What happened | Why (as far as known) |
|---|---|---|---|
| 1 | Rules, Lenskart `registrar` | Read "Link Intime India Private Limited"; gold "MUFG Intime India Private Limited". | The cover prints "MUFG Intime India … Private Limited (Formerly Link Intime India Private Limited)" (gold quote, page 2); the known-name rule (ADR-036) matched the old name inside the parenthesis. Confirmed from the gold quote. |
| 2 | Rules, Groww `promoters` | Read three promoters, gold has four (Neeraj Singh missing). | The list ends early; list spans are the weakest part of the cover rules (see also the dot-after-initial bug, ADR-041). |
| 3 | Rules, LG `ofs_shares` | Read nothing; gold "101,815,859 equity shares". | LG is a pure offer for sale with a different cover layout; no pattern matched, and the rule abstains rather than guess. |
| 4 | Fine-tuned, Meesho `registrar` | Read "Citigroup Global Markets India Private Limited"; gold "KFin Technologies Limited". | A book-running lead manager's name was read as the registrar: both sit in the same cover block (*likely*). Tata Capital shows the same confusion (an SBI Capital Markets reading). |
| 5 | Fine-tuned, Lenskart `total_issue_size` (Prospectus) | Read ₹51,280.15 million; gold ₹72,780.15 million. | Another amount on the page (a component of the offer) was read as the total. The verifier cannot catch this: the number is in the passage. |
| 6 | Fine-tuned, Groww / Lenskart / Meesho `ofs_amount` (RHP) | Read ₹10,600.00, ₹21,500.00 and ₹42,500 million where the RHP prints "₹ [●] million". | The model reads a nearby real number for a placeholder. The placeholder logic in `select_field` is the guard, not the model (ADR-018 consequence 2). |
| 7 | Verifier (E5), test IPOs | 5 `scale_lakh_crore` items were reported as `wrong_value` instead of `scale_mismatch`. | The first rule set needed a scale signal that those test passages did not print in the same cell (`verifier.json`, `held_out_misses`). One rule fix followed: 40/40, but not held-out (ADR-044). |
| 8 | Guard, fresh probes | 3 of 36 advice probes were not blocked on the first run ("I should …" decisions, the plural "investors", two accounts). | The rules were written from the 60-question set; unseen phrasings slip through. Fixed after scoring, so only the first-run 33/36 is an unseen estimate (ADR-046). |
| 9 | Hindi answer, Ather fresh issue (fluency sheet) | "₹10,527 million … ₹26.260 करोड़" for a fresh issue of ₹26,260 million. | A scale slip (million written as crore with a moved decimal) plus a wrong figure from another passage. The verifier marks both ❌; without it the sentence reads as fluent Hindi (`data/gold/hindi_fluency_sheet_rated.csv`). |
| 10 | Hindi use-of-money, LG | "I could not find this" although the objects table is in the passages (and the English answer says the company receives no money). | The 2B model is weak in Hindi and the pure-OFS case has no objects table to pin (ADR-053; `docs/MORNING_REPORT.md`). Unfixed. |

## What the failures have in common

- **Name fields are the hard ones** (managers: 0.29 for rules and 0.10 for the fine-tuned model on the full
  document; registrar and promoters 0.71 to 1.00): lists, renamed firms and neighbouring blocks.
- **Placeholders** (`[●]`) in an RHP are a trap for a reader trained on filled-in Prospectuses; the guard is
  a rule, not the model.
- **The verifier checks consistency with a passage, not truth.** Failure 5 passes every check: a correct number
  in the wrong role. The report must not say verified means correct.
- **Language**: the same fact is easier in English than in Hindi at 2B parameters (§7.5).

## E7 answer-level failures

*To be filled from `eval_results/e7_turns_*.jsonl` after the E7 run (section 7.3).*
