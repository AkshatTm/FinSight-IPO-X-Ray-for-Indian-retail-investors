# Datasheets

One datasheet per dataset (B09 §5, after "Datasheets for Datasets"). Counts are generated from `eval_results/` and `data/gold/`.

| Dataset | What it is | Datasheet |
| --- | --- | --- |
| Training corpus | Text of 389 older Indian IPO offer documents (Ghosh et al.) | [Corpus](corpus.md) |
| Weak labels | Automatically made training examples for the extractors | [Weak labels](weak_labels.md) |
| Gold sets | Hand-checked values, questions and guard examples used for scoring | [Gold sets](gold_sets.md) |
| Teacher outputs | Labels and rewrites for corpus risk factors, written by an open-weight teacher model | [Teacher outputs](../phase2/datasheets/teacher_outputs.md) |

Planned with Phase 2 local parts, each with its own datasheet when it exists: the risk bank (B2.2b) and segmentation gold (B2.1b).
