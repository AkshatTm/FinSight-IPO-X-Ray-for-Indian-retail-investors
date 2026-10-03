# Datasheet: weak labels

## Motivation

Hand-labelling enough passages to fine-tune an extractor is too slow for one person. Weak labels give thousands of examples for free, at the cost of some noise that the audit measures.

## Composition

SQuAD 2.0 examples (question, passage, answer span or "no answer") for eight offer fields, split by IPO into train and dev (no IPO in both). BIO-tagged copies feed the BiLSTM-CRF. Counts from `eval_results/weaklabel_stats.json` and `weaklabel_audit.json`:

<!-- generated:stats start -->

Label version 2, split seed 2026. Train: 272 IPOs, 4047 examples (1624 with an answer). Dev: 30 IPOs, 491 examples (194 with an answer).

| Field | Seed found (IPOs) | Positives | Negatives |
| --- | --- | --- | --- |
| `fresh_issue_size` | 109/389 | 171 | 252 |
| `ofs_shares` | 136/389 | 182 | 272 |
| `ofs_amount` | 96/389 | 136 | 209 |
| `total_issue_size` | 127/389 | 173 | 258 |
| `face_value` | 255/389 | 893 | 1339 |
| `book_running_lead_managers` | 110/389 | 85 | 121 |
| `registrar` | 99/389 | 90 | 139 |
| `promoters` | 127/389 | 88 | 130 |

Audit (E1, measured on labels v1; current v2): 45/50 correct, precision 0.90 [0.79, 0.96]. Errors: wrong span 3, wrong value 2, ambiguous 0. Audit labels: `ai_labelled_claude_chat_human_reviewed`.

<!-- generated:stats end -->

## Labelling process

1. **Seeds:** rules read each value from the cover page of a corpus document (`finsight.weaklabel.seeds`), and where the Excel sheet holds the same value the two are compared.
2. **Propagation:** a body passage becomes a positive when it holds the same value (compared with `normalize.equal`, so ₹ 3,000 million equals Rs. 300 crore) near a word naming the field (`finsight.weaklabel.propagate`).
3. **Negatives:** one or two passages from the same sections without the value, chosen with a fixed seed (`finsight.weaklabel.negatives`).

No person or AI model wrote these labels; they are fully automatic. The 50-row **audit** was labelled with AI help and reviewed by Akshat (`label_source` in `data/gold/weaklabel_audit.jsonl`).

## Known problems

- Version 2 fixed the audit's misses (face values of preference shares, cut names, lists); it has not been re-audited.
- Values only on the cover page give no body positives, so some fields have far fewer examples.

## Uses

Training and validating the extractors only. Never as a scoring set: scores use the [gold sets](gold_sets.md).

## Distribution and licence

Derived from the CC BY-NC-SA 4.0 corpus; not committed. Rebuild with `python -m finsight.weaklabel`.
