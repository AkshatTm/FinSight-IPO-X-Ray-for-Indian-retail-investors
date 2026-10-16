# FinSight Bench v1: error analysis (C4.1)

Ten real failures across the systems that have run, picked by a fixed rule before reading them
(`scripts/bench_score.py::failures`: round-robin over (system, task), failing items in
sha256 order of their id, a fixed shuffle). The table is regenerated from `eval_results/c4/bench_failures.json` by
`uv run poe docs-gen`; nothing in it is typed by hand. Every row is from a single run.

The bench IPOs are test-slice documents (C-ADR-02). This page is descriptive: none of these
failures may be used to tune prompts, thresholds or training data (C-ADR-06, C-ADR-24). Fixes go
to bench v2 with new IPOs.

## The ten failures

<!-- generated:failures start -->

| # | System | Task | Item | What happened |
| --- | --- | --- | --- | --- |
| 1 | rules_v1 | A | `A:groww-2025:general_purposes_pct_of_fresh@final` | `general_purposes_pct_of_fresh@final`: gave not_found (p None), gold [●] (p 29) |
| 2 | rules_v1 | C | `C:groww-2025:a4` | answerable → wrong; gold 26,092.81; said: The document states Revenue from Operations were ₹ 29,086.51 million for FY ended March 31, 2024 [1]. The tex… |
| 3 | rules_v1 | B | `B:lg-electronics-india-2025:RF07` | `RF07`: ok, gold not_applicable |
| 4 | student | A | `A:groww-2025:general_purposes_pct_of_fresh@final` | `general_purposes_pct_of_fresh@final`: gave 35 (p 151), gold [●] (p 29) |
| 5 | student | B | `B:groww-2025:RF02` | `RF02`: not_available, gold watch |
| 6 | rules_v1 | A | `A:groww-2025:peer_pe_list@final` | `peer_pe_list@final`: gave [Decimal('19.80'), Decimal('24.88'), De… (p 166), gold Angel One 24.88; Motilal Oswal 19.80; 3… (p 165) |
| 7 | rules_v1 | C | `C:tata-capital-2025:u1` | unanswerable → wrong; gold none (unanswerable); said: The document states that for all individual stocks, including Emcure Pharmaceuticals Ltd., the closing price… |
| 8 | rules_v1 | B | `B:lg-electronics-india-2025:RF11` | `RF11`: not_available, gold ok |
| 9 | student | A | `A:groww-2025:peer_pe_list@final` | `peer_pe_list@final`: gave [] (p None), gold Angel One 24.88; Motilal Oswal 19.80; 3… (p 165) |
| 10 | student | B | `B:hdb-financial-services-2025:RF02` | `RF02`: not_available, gold concern |

<!-- generated:failures end -->

## Reading

PENDING
