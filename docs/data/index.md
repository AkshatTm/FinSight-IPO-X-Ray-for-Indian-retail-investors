# Corpus, splits and licences

FinSight's data comes from public Indian IPO offer documents. No PDF is in the repository; the
committed files are configs, manifests, gold labels and a small fixture pack of text excerpts
(`tests/fixtures/real/`, B-ADR-15). Each dataset has a datasheet in the
[Datasheets for Datasets](https://arxiv.org/abs/1803.09010) format ([Datasheets](../datasheets/index.md)).

## Two corpora

| Corpus | Size | Source | Used for |
| --- | --- | --- | --- |
| Ghosh et al. Indian IPO corpus | **389** IPOs, 2009–2023 (279 prospectuses, 110 RHPs; median 450 pages) | Hugging Face `sohomghosh/Indian_IPO_datasets`, CC BY-NC-SA 4.0 | weak labels for the extractor, train-slice risks, the risk bank |
| Recent RHPs (2024–2026, by SEBI posting date) | **289** in the universe; **275** parsed, **14** excluded with reasons (12 SME, 2 without numbered risk factors) | SEBI and exchange filings, `configs/ipo_universe.csv`, fetched by `scripts/fetch_offer_docs.py` | the time split, dev / test / bench, the risk bank, reference scores |

Sources: `eval_results/corpus_stats.json` and C05 roadmap part C1 (summarised in
[FINAL_SCORECARD](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/final/FINAL_SCORECARD.md#corpus-and-splits-carried)).
SME IPOs are excluded by decision (C-ADR-09): their documents follow a different format and they are not
open to the same investors.

## The time split (C-ADR-02)

`configs/splits.yaml` is written by `uv run python -m finsight.splits build` and **frozen**
(`frozen: true`, rule `strict`). It changes only by a new C-ADR (it was changed once, by C-ADR-24, to
create the bench).

| Slice | Contents | May be used for |
| --- | --- | --- |
| train | 389 corpus IPOs + 110 recent RHPs from before the train cut (`train_cut: 2025-06-19`) | training data, the risk bank, weak labels |
| dev | 52 recent RHPs + 3 showcase IPOs | choosing models, thresholds, rules and prompts |
| test | 103 recent RHPs + 7 showcase IPOs | reported numbers only |
| bench | 7 of the test IPOs, frozen inputs | FinSight Bench v1 only ([Bench](../evaluation/bench.md)) |
| demo | the 3 newest RHPs | the live demo only |
| excluded | 14 | nothing |

**Leakage rules.** Documents in the `test` or `bench` slices never enter training data, the risk bank,
thresholds or prompt tuning. The risk-level thresholds were fitted on 165 train + dev IPOs with full
documents (C-ADR-25); the risk bank holds 29,677 risks from 440 IPOs (C-ADR-25). The committed manifests
in `data/manifests/` list which IPOs each training file used, and `tests/test_split_leakage.py` fails
when a test or bench IPO appears in one. The 10 showcase IPOs are also listed in
`data/gold/excluded_ipos.txt`, which the corpus builder drops. Where a decision was informed by test
results it says so ("test-informed"), for example gold v3.1 and the extractor v2 ladder row.

## Gold sets

Hand-checked labels used for scoring; full details on [Gold sets](../datasheets/gold_sets.md).

| Set | What | Size | Labels | Used by |
| --- | --- | --- | --- | --- |
| gold v3 | Summary facts and red-flag statuses of the 10 showcase IPOs | 280 rows (195 with a value); 130 red-flag statuses | AI pre-fill, verified on the page by Akshat | E14, E15 |
| gold v3.1 | Gold v3 with 11 rows changed by four convention fixes (C-ADR-22) | 280 rows | as v3, plus documented fixes (`data/gold/gold_v3_1_changelog.md`); test-informed | E14 / E15 history rows |
| gold-150 | 150 risk factors from test IPOs with category and band | 150 | model pre-fill, Akshat agreed with 132 and changed 18 ([source](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/c/gold150_verification.json)) | classifier test |
| gold-50 | 50 risks from 10 test IPOs, rewritten by base, student and teacher | 50 × 3 | blind, shuffled ratings by one rater | student evaluation (E18) |
| Phase 1 gold | Cover facts and chat questions of 7 test IPOs | see datasheet | AI-assisted, checked | extractor ladder, E7 |
| L2 event labels | Sentences around serious findings labelled actual / hypothetical / negated / not relevant | 1,007 sentences from 275 IPOs (416 train, 194 dev, 397 test) | AI (`label_source: "ai"`), verification sheet of 481 rows prepared | written for the Phase 4 event classifier (M3), which was cut; not used by the product |

The L2 card is `data/gold/event_labels/LABELS_CARD.md` (written by ARGON in Phase 4).

## Licences of the source documents

- **Offer documents** (DRHPs, RHPs, prospectuses) are public filings with SEBI and the exchanges.
  FinSight downloads them from the official sources only, politely, and never re-hosts them (C-ADR-08).
  The repository holds no PDFs; the fixture pack holds short text excerpts for tests.
- **The Ghosh et al. corpus** is CC BY-NC-SA 4.0. Anything trained on it (the field extractor, and
  through the teacher's training pairs the classifier and the student) is non-commercial and
  share-alike.
- **Teacher outputs** were written by Gemma-4-31B-it, so the Gemma terms of use apply to them.

See [NOTICE](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/NOTICE)
for every third-party licence.
