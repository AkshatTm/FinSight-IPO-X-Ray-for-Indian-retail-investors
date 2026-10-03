# Real-section fixture pack (B-ADR-15)

Lets cloud sessions develop against **real** offer-document pages without the PDFs.
Written only by `scripts/export_fixtures.py` (local session); never edit by hand.
Re-run after changing section patterns: `uv run python scripts/export_fixtures.py`.
Size: ~15 MB of 20 MB, no file over 5 MB, no PDFs or weights (checked by `tests/test_fixture_pack.py`).

## Contents

| Path | What |
|---|---|
| `<ipo_id>/rhp.pages.json.gz` | RHP pages of: cover, Summary, The Offer, Summary Financial Information, Capital Structure (first 15 pp.), Objects (first 20), Basis for Offer Price, Risk Factors (all), Financial Indebtedness (4), Outstanding Litigation (12), plus restated **cash-flow** (≤ 4) and **auditor's report / qualification** (≤ 8) pages. Per page: number, printed page, size, text, words `[text,x0,y0,x1,y1,font_size,bold]`. Also all found `sections`, `kept` (label → pages) and pre-extracted `tables` (PyMuPDF `find_tables`, cells `[row,col,text,x0,y0,x1,y1]`) |
| `<ipo_id>/prospectus.pages.json.gz` | Final Prospectus: cover, The Offer, Basis for Offer Price (prices) |
| `corpus_risk_factors/*.txt.gz` | Risk Factors text of 20 corpus RHPs, round-robin over 2015–2023; pages joined by `\f`. `index.json` lists them |
| `corpus_stats.json` | Copy of `eval_results/corpus_stats.json` |
| `samples/parsed_*.json.gz`, `samples/xray_*.json.gz` | Shape samples for 2 IPOs (parsed truncated to the first 12 pages) |
| `fake_training/risks_20.jsonl` | 20 **synthetic** risks with category + plain rewrite (`label_source: synthetic`) for notebook smoke tests |
| `loader.py` | `load_doc`, `load_sections`, `kept_pages`, `load_tables`, `corpus_risk_factors`, `fake_risks`, `RF_SOURCES` |

IPOs: the 10 showcase IPOs of `configs/demo_ipos.yaml`. In a loaded `ParsedDoc`, `pages` holds only the exported pages; `Page.number` is the real PDF page, so use `page_map(doc)`.

## Red flag → source pages

| Check | Reads | Label(s) in `kept` |
|---|---|---|
| RF01 profit | summary financials | `summary_financial_information` |
| RF02 cash from business | cash-flow statement | `cash_flows`, else `summary_financial_information` |
| RF03 debt | summary financials | `summary_financial_information` |
| RF04 who gets the money | offer + objects | `the_offer`, `objects_of_the_offer` |
| RF05 insider price | basis for offer price | `basis_for_offer_price` |
| RF06 promoter stake | capital structure | `capital_structure` |
| RF07 vague use of money | objects | `objects_of_the_offer` |
| RF08 court cases | litigation | `outstanding_litigation`, `summary` |
| RF09 related parties | financials | `summary_financial_information`, `restated_financial_information` |
| RF10 customer concentration | risk factors | `risk_factors`, `summary` |
| RF11 price vs peers | basis for offer price | `basis_for_offer_price` |
| RF12 auditor's remarks | auditor's report | `auditors_report`, `summary_financial_information` |
| RF13 pledged shares | capital structure | `capital_structure` |

## Known gaps (from the 3 Oct export)

- **tata-capital-2025:** no restated cash-flow page found by heading (`cash_flows` empty); RF02 falls back to the summary financials.
- Only the first 15 (Capital Structure) / 20 (Objects) pages are kept; promoter pledge or objects tables beyond that are missing.
- Restated financial statements are **not** exported in full (only the cash-flow and auditor pages), so related-party notes (RF09) come from the summary pages only.
- Tables are PyMuPDF ruled-line tables only; unruled tables (Docling would recover them) may appear as headers only.
- No `report.json` sample: no Phase 2 report exists locally yet (B1.3b will produce one).

## Sources and licences

Offer documents are public SEBI filings (RHP / Prospectus of the listed companies). Corpus excerpts come from the IPO dataset of Ghosh et al., **CC BY-NC-SA 4.0**, used for non-commercial research. The fake training set is invented text.
