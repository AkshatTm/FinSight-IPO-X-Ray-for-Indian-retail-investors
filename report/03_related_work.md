# 3 Related work

> **DRAFT — Akshat to rewrite in his voice.** Every citation is from Claude's memory and marked
> `[verify]`: look each one up and fix the year and venue before it goes in the report.

**Question answering over financial documents.** Numerical reasoning over reports is studied with
FinQA (Chen et al., 2021) [verify], TAT-QA (Zhu et al., 2021) [verify] and ConvFinQA [verify], which
ask for calculations over tables and text in company filings. FinanceBench (Islam et al., 2023)
[verify] measures how well language models answer questions about public filings and reports that
even strong systems fail often without the document. These benchmarks use US filings in English.
FinSight differs in scope: Indian offer documents (RHP and final Prospectus), no calculation, and
a checker for the numbers in the answer, in English and Hindi.

**Extraction without labelled data.** Distant supervision (Mintz et al., 2009) [verify] builds
training data by aligning a knowledge source with text. Here the seeds are high-precision cover-page
rules, propagated to other passages by normalised value match (ADR-003, ADR-038) and used to fine-tune
an extractive reader (DeBERTa-v3, He et al., 2021 [verify]; SQuAD 2.0 format, Rajpurkar et al.,
2018 [verify]). A BiLSTM-CRF tagger (Huang et al., 2015; Lample et al., 2016) [verify] is the
classical sequence-labelling baseline and is the fourth rung of our ladder.

**Retrieval-augmented generation and grounding.** Retrieval-augmented generation (Lewis et al.,
2020) [verify] conditions an answer on retrieved passages. We use BM25 (Robertson and Zaragoza,
2009) [verify], dense retrieval with BGE-M3 (Chen et al., 2024) [verify] and a cross-encoder
reranker. Citation quality of generated answers is studied by ALCE (Gao et al., 2023) [verify]; RAGAS
(Es et al., 2023) [verify] scores faithfulness with another model. We take a different route for
numbers: a deterministic checker (ADR-004) rather than a model judge, because a number is either
in the cited passage with the right unit or it is not.

**Fact verification.** FEVER (Thorne et al., 2018) [verify] frames verification as three labels
(supported, refuted, not enough information), which our marks mirror (✅, ❌, ⚠️ unverifiable).
Natural-language-inference models can check non-numeric claims; that is the optional P5.5 check.

**Indian-language NLP and speech.** MuRIL (Khanuja et al., 2021) [verify] is a BERT model for
Indian languages and is the encoder of our optional advice classifier; Whisper (Radford et al.,
2023) [verify] and faster-whisper provide Hindi speech recognition. Hindi generation by small
open models is weak in our measurements (mean fluency 2.9 of 5, draft ratings; ADR-020).

**Positioning.** To our knowledge there is no public tool that reads an Indian RHP, shows every
fact with its page, and checks the numbers of a bilingual chat answer with local open-weight
models [verify: do a short search before claiming this]. SEBI's rules on investment advice are why
the system refuses advice, ratings and predictions (ADR-005, ADR-046).
