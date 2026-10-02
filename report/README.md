# Report drafts

> **DRAFT — Akshat to rewrite in his voice.** Everything in this folder was drafted by Claude Code
> from the committed results (`eval_results/`) and the decision records (`docs/09_DECISIONS.md`).
> Akshat owns every claim: read each number against its source file, delete what he cannot
> defend, and write the final text himself. Sections 1, 2, 9 and 10 are not drafted here.

| File | Section |
|---|---|
| `03_related_work.md` | 3 Related work (citations marked `[verify]`, check each before use) |
| `04_data.md` | 4 Data and licences |
| `05_preprocessing.md` | 5 Preprocessing, including Indian numeral normalisation |
| `06_method.md` | 6 Method |
| `07_results.md` | 7 Results |
| `08_error_analysis.md` | 8 Error analysis (ten real failures) |
| `11_reproducibility.md` | 11 Reproducibility statement |

## Disclosures that must appear in the final report

1. **AI-assisted gold labels.** Gold v1 (80 ladder values and the wider 110-value set) was
   pre-filled by Claude (chat) from the PDFs and then checked by Akshat (`label_source =
   ai_assisted_verified`, ADR-035). The hand corrections are not recorded. A blind
   self-consistency re-label is still to be done by hand.
2. **AI-drafted audit and question sets.** The 50-row weak-label audit, the question sets
   (`questions_dev/test`) and the advice-guard set (60 advice + 60 factual) were drafted by Claude
   chat. None of the advice-guard rows has been reviewed by Akshat; the guard rules were tuned
   after reading that set, so its 60/60 result is in-sample (ADR-046). The unseen estimate is
   the 85 fresh probes (33/36 advice blocked on the first run).
3. **Test-informed revert.** At G2 `fresh_issue_size` and `total_issue_size` were switched back
   to rules-first after the test results showed the dev-only choice cost accuracy. That is not a
   clean held-out choice; the dev-only configuration is kept and reported (0.857 vs 0.875, one
   value of 56).
4. **Held-out versus tuned verifier numbers.** The verifier's 35/40 scale-mismatch recall is the
   held-out figure (rules frozen on the three dev IPOs); 40/40 is after one rule fix made on
   seeing the five test misses and is not held-out (ADR-044).
5. **Hindi fluency scores** are Claude drafts pending Akshat's confirmation (ADR-020 is
   provisional until then). The ASR references are Claude's reading of what was said
   (0 of 10 reviewed by Akshat).
6. **Small samples.** Seven test IPOs, 56 test values, 18 held-out guard questions: every
   interval is wide. Report paired differences and intervals, not point scores.
