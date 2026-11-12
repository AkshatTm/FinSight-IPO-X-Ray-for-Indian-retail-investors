# Datasheets

One datasheet per dataset, following "Datasheets for Datasets" (Gebru et al.): motivation, composition,
collection, preprocessing, uses, distribution and maintenance. Counts between `generated` markers come
from `eval_results/`, `configs/` and `data/gold/` (`uv run poe docs-gen`). The overview of all data,
the time split and the licences is [Corpus, splits and licences](../data/index.md).

| Dataset | What it is | Datasheet |
| --- | --- | --- |
| Training corpus | Text of 389 older Indian IPO offer documents (Ghosh et al., 2009–2023) | [Corpus](corpus.md) |
| Recent offer documents | 289 mainboard RHPs posted on SEBI 2024–2026; 275 parsed | [Recent IPOs](new_ipos.md) |
| Risk bank | 29,677 past risk factors from 440 train + dev IPOs, with bge-m3 vectors | [Risk bank](risk_bank.md) |
| Weak labels | Automatically made training examples for the field extractor | [Weak labels](weak_labels.md) |
| Gold sets | Hand-checked values, statuses, ratings and questions used for scoring | [Gold sets](gold_sets.md) |
| Teacher outputs | Labels and rewrites of train-slice risks by Gemma-4-31B-it | [Teacher outputs](../phase2/datasheets/teacher_outputs.md) |
| L2 event labels | 1,007 AI-labelled sentences around serious findings (Phase 4, unused) | [LABELS_CARD.md](https://github.com/AkshatTm/Vidura-IPO-X-Ray/blob/main/data/gold/event_labels/LABELS_CARD.md) |
