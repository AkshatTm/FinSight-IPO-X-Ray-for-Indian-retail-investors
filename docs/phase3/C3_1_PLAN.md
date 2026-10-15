# C3.1 plan — summary + financial extraction + E14 (approved by Akshat)

Rules for every item: each value is a `SummaryValue` with page evidence and a status (`found`,
`placeholder`, `not_found`, `stated_zero`); nothing is guessed. Tuning on `dev` IPOs only
(C-ADR-02); the real E14 run waits for gold v3 verification.

## C3.1a — financial tables + stage (PR #224)

1. `summary/__init__.py`: `build(parsed, sections) -> FinancialSummary` (`extract_summary`, and
   `build(storage, doc_id)` for the stage).
2. Tables (`summary/layout.py`, `summary/periods.py`, `summary/financials.py`): restated
   financials → revenue, PAT, operating cash flow (3 full fiscal years, latest first), total
   borrowings, net worth; unit from the table header. Balance-sheet values: the latest full
   fiscal-year-end value is primary; the latest stub-period value is kept as a secondary field
   with its date. A dash / "Nil" in an otherwise numeric row is `stated_zero`.
7. Non-critical `financials` stage after `sections`; a failure does not stop the job.

## C3.1b — the other red-flag inputs

3. `litigation.py`: criminal case count + total amount from the outstanding-litigation summary.
4. `holdings.py`: promoter post-issue holding, pledged %, promoter WACA, identifiable-promoter flag.
5. `customers.py` top-1 / top-10 customer share; `objects.py` general-corporate-purposes %;
   related-party transactions total.
6. `peers.py` reusing the compare peer-table parser; `auditor.py`: CARO, qualifications,
   emphasis of matter; is-financial-company flag (routes banks, NBFCs and insurers to their own
   statement layouts).
8. Tests: fixture tests per field, stage wiring test, scorer test.
9. `scripts/summary_eval.py` → `eval_results/b/summary_extraction.json` (E14; dev for tuning only;
   the real run waits for gold v3).
10. Docs: Part C section in `docs/10_FINSIGHT_EXPLAINED.md` + docs-gen.

## Follow-ups (not in C3.1)

- `parse` misses "Summary of the Offer Document" in 16/55 dev RHPs; `summary` scans the 40 pages
  before Risk Factors instead. The fix belongs in `parse`, scheduled with the heading-denylist task.
