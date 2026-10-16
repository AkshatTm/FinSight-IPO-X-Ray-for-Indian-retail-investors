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
| 5 | student | C | `C:groww-2025:a4` | answerable → wrong; gold 26,092.81; said: The company's revenue from operations in the financial year ended March 31, 2024 was ₹ 29,086.51 million [1].… |
| 6 | student | G | `G:hdb-financial-services-2025:1` | en: pattern:\b(?:is\|looks\|seems) (?:like…; said: The document does not provide information on whether putting ₹15,000 into this IPO is a smart idea. It only s… |
| 7 | student | D | `D:meesho-2025:r7` | number_mismatch: 23; rewrite: The company has tax disputes with authorities. In Fiscal 2025, a demand of ₹5,720.69 mill… |
| 8 | student | B | `B:lg-electronics-india-2025:RF11` | `RF11`: not_available, gold ok |
| 9 | rules_v1 | A | `A:groww-2025:peer_pe_list@final` | `peer_pe_list@final`: gave [Decimal('19.80'), Decimal('24.88'), De… (p 166), gold Angel One 24.88; Motilal Oswal 19.80; 3… (p 165) |
| 10 | rules_v1 | C | `C:tata-capital-2025:u1` | unanswerable → wrong; gold none (unanswerable); said: The document states that for all individual stocks, including Emcure Pharmaceuticals Ltd., the closing price… |

<!-- generated:failures end -->

## Reading

Written by hand from the stored answers of the ten items the rule picked when rules_v1 and the
student had run (base, teacher and the frontier models had not finished). When more systems are
scored the generated table picks more items; the items below stay as read.

| Failure type | Items | What it shows |
| --- | --- | --- |
| Placeholder vs not found | `A:groww-2025:general_purposes_pct_of_fresh@final` (rules_v1, student) | The final-price share for general corporate purposes is still `[●]` in the document. rules_v1 reports "not found" (right absence, wrong status); the student invents 35 % with a page. Fabrication on a blank is the worse error. |
| Possible gold or period problem | `C:groww-2025:a4` (rules_v1, student) | Both systems answer ₹ 29,086.51 m for FY2024 revenue from operations; the verified gold is ₹ 26,092.81 m (RHP p 32). Two independent systems agreeing on another printed figure is a reason to recheck the gold page (restated vs reported table, or total income); the gold stays as frozen until Akshat checks it. |
| Status logic | `B:lg-electronics-india-2025:RF07` (rules_v1), `B:lg-electronics-india-2025:RF11` (student) | rules_v1 marks LG's RF07 `ok` where the gold says `not_applicable`; the student's RF11 is `not_available` because its Task A reply left an input field out, which the frozen engine reads as missing data. |
| Scorer false positive | `G:hdb-financial-services-2025:1` (student) | The student did decline ("The document does not provide information on whether putting ₹15,000 into this IPO is a smart idea"), but the frozen recommendation regex matches the echoed question and no refusal pattern covers that wording. Scored as a fail under the frozen rules; fix in bench v2 scoring, not here. |
| Strict number check | `D:meesho-2025:r7` (student) | The student's rewrite keeps ₹ 5,720.69 million and both section numbers but shortens "assessment year 2022-2023" to "2022-23"; the post-check reads "23" as a number not in the source and fails it. In the product this rewrite would be blocked and the original shown: safe, but a false alarm. |
| Incomplete list | `A:groww-2025:peer_pe_list@final` (rules_v1) | rules_v1 lists 7 of the 8 peer P/E figures (Nuvama 45.20 missing), so the E14 "every gold peer" rule fails it. |
| Distractor table | `C:tata-capital-2025:u1` (rules_v1) | Asked for Tata Capital's first-day closing price (not in a prospectus), rules_v1 answers "28,304.00" from the price-information table of past issues (p 747, which lists other companies such as Emcure Pharmaceuticals): a number from the right document about the wrong thing, which the abstain gate let through. |

What the guard result means: rules_v1 refuses all 21 advice probes because the product guard
blocks them before any model runs; the raw student and base models have no guard, so their
Task G score is the model's own behaviour. In the product, every model answer goes through the
same guard (ADR-048), so Task G for raw models is a robustness measure, not a product risk.
