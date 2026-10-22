# CC-05a — Jio red-flag diagnosis (fixed in CC-05b + CC-06, see the result below)

**Test-informed:** Jio (`jio-platforms-2026`, upload `doc_72480c2e249eb8da`, 591 pp.) is in `excluded_ipos.json`. It is the one disclosed parser-diagnosis exception (P4_PLAN §2). Nothing here tunes a threshold.
Method: re-ran `summary.extract_summary` + `redflags.evaluate` on the stored parse with current code (same result as the stored `redflags.json`, so it isn't a stale cache), then probed the pages each reader needs.

## Result after CC-05b + CC-06
**Jio: 7 of 13 checks are decided from the RHP alone** (was 1/13): RF01 ok (PAT ₹300,527 mn), RF02 ok, RF03 ok (D/E 0.21), RF04 ok (fresh issue only), RF08 watch (about 27 criminal cases, counted from sections, approximate), RF12 ok, RF13 ok. Pinned by `tests/summary/test_sod_jio.py` (`@local`).
- **Still undecided:** RF09: Jio prints RPT by transaction type only, with no overall total, so it is "not found" with that reason. The per-party sums were not added, to avoid mixing transaction types. RF10: not disclosed. RF05/06/07/11: they need the price band; without a band they will show `PENDING_PRICE`; with ₹1,065–1,119 entered, Jio could reach at most 11/13 (not measured yet; done in CC-07).
- **Serious findings:** p.40 is gone (the "in case of" hedge). Only p.472 (SEBI order on the Promoter) remains, left for the C-ADR-26 rule in CC-07.
- RF06 now reads pre-offer 66.43%; the post-offer value is a placeholder until the Prospectus.

## Root cause
**Jio's RHP has no "Summary of the Offer Document".** The TOC goes Risk Factors (30–71) → Section III Introduction: The Issue (72–73), Summary Financial Information (74–78), Summary of Contingent Liabilities (79), Summary of RPT (80–86). Six readers only look at the SOD (`summary_pages`). When there's no SOD, `summary_pages` falls back to the 40 pages before Risk Factors, which for Jio means pp. 1–29: cover, definitions, conventions. They find nothing there.

## (a) Per check
| Check | Input it needs | What the reader returned | Where it broke | Fix |
|---|---|---|---|---|
| RF01 Profit | PAT, 3 FY | `not_found` ×3 | **locate** (no SOD) + **table parse**: on the SFI P&L (p.76) the "Fiscal" header spans 3 columns but only the middle one gets it (`2026`, `Fiscal 2025`, `2024`). The bare years sit next to stub columns, so they're skipped, and then the safety rule (an unranked later year) refuses every year. The revenue and PAT rows are found. | S–M |
| RF02 Cash | Operating cash flow | found ₹775,563 mn (p.334) | works | — |
| RF03 Debt | Total borrowings + net worth | `not_found` | **locate** + **field mapping**: the SFI balance sheet (p.75) has no "Total equity" or "Total borrowings" row, only Equity share capital + Other equity and Borrowings (non-current) + Borrowings (current). The borrowings sum runs only on the SOD table. | M |
| RF04 Who gets the money | Fresh ₹ / OFS ₹ (X-Ray cover) | 0 candidates for both | **table parse**: the cover is a 4-column table ("Fresh Issue \| Up to 270,000,000 shares … ₹[●] million \| Not applicable \| …"), and the cover rules expect "fresh issue of …" prose. Also **check logic**: a pure fresh issue (OFS "Not applicable") can be decided even when the ₹ is [●]. | M |
| RF05 Insider price | Promoter WACA + offer price | WACA `[]`, price [●] | **locate**: the WACA table is on p.113 (Capital Structure); the reader looks only in the SOD. Even once found, the price is [●] in an RHP, so "until the price is set" is the correct result. | S (still N/A until the price is set) |
| RF06 Promoter stake | Post-offer promoter % | `None` | **locate** (table on p.109, Capital Structure) + **wording**: `_POST` matches only "post-offer", and Jio says "post-Issue". The printed post value is [●] (pre-issue 66.43%), so the result would be `placeholder`. | S–M (then placeholder) |
| RF07 Vague use of money | GCP % of fresh | `placeholder` p.116 | Not a bug: the objects table prints GCP as [●]. The sentence wrongly says "couldn't find" when it should say "not set yet". | S (message) |
| RF08 Court cases | Criminal count + amount (SOD table) | `{}` | **locate**: there's no SOD litigation table. The chapter (pp. 463–474) is narrative under headings ("Criminal proceedings against the Company / by the Company / against the Subsidiaries"), with 0 anchored tables. | L |
| RF09 Related parties | RPT total, latest FY | `None` | **locate** (the `summary_of_related_party_transactions` section, pp. 80–86, exists but isn't read) + **field mapping**: the tables have per-party and per-type "Total" rows but no single grand total. | M |
| RF10 Customers | Top-1 / top-10 % | `None` | Nothing to fix: consumer telecom, no customer-share disclosure (only "largest customer base" claims). | — |
| RF11 Price vs peers | Issuer P/E + peer median | issuer P/E none (EPS 33.63); Bharti 40.71, Vi 3.99 | Correct: P/E at floor/cap is printed [●] (p.129). It waits on the price. | — |
| RF12 Auditor | Remark statement | `[]` | **locate** (the SOD statement is absent) + **check logic**: p.430 (Restated annexure) says "There are no audit qualification … no Emphasis of matters", but it isn't read, and an empty list gives N/A where OK would be right. | S–M |
| RF13 Pledged shares | Pledged % (shareholding pattern, row (A)) | `None` | **table parse**: in the p.107 pattern the pledged columns are "-", but the anchored reader fails on the narrow, split header cells ("encumbere"). | M |

**What fixing gets us on Jio (RHP only):** RF01, 03, 04, 09, 12, 13 become decidable, which with RF02 makes 7/13. RF08 makes 8 (L). RF05/06/07/11 stay "until the price is set" because their inputs are [●] in any RHP, and RF10 isn't disclosed. **The P4-G2 target (≥10/13) is reachable on Jio only if "until the price is set" counts as answered, or if the final Prospectus is added.** Akshat to decide.

## (b) The two serious findings
| Finding | Page / section | Matched sentence | Context | Verdict | Should the filter have blocked it? |
|---|---|---|---|---|---|
| Loan default or recall | p.40, Risk Factors | "Covenants under our debt agreements require us to obtain consents in certain situations, including entering any scheme of merger, amalgamation, consolidation or corporate reconstruction and declaring or paying any dividend **in case of delay or default in the repayment** of facilities availed." | Before: "Insufficient financing could delay …". After: "Approvals may not be granted …; we are also required to maintain certain financial covenants." | **Hypothetical** (a covenant condition) | **Yes.** `_SOFT` has "if" and "in the event" but not "in case of". False positive. |
| Regulator order | p.472, Outstanding Litigation (Promoter RIL) | "The Adjudicating Officer of Securities and Exchange Board of India passed an order on June 20, 2022, imposing a penalty of ₹3 million." (2nd hit: "(ii) SEBI, on August 8, 2014, had passed an adjudication order … and imposed monetary penalty of ₹130 million.") | Before: SEBI show-cause notice to **RIL** (the Promoter), UPSI disclosure. After: SAT dismissed RIL's appeal (2 May 2025), the Supreme Court dismissed it (2 Dec 2025). The 2nd order was **set aside** by SAT (next sentence). | **Real event**, but against the Promoter, not Jio, for ₹3 mn (₹0.3 cr). The 2nd hit is a real order, later set aside. | **No.** It isn't negated or hedged, so the filter worked as written. The problem is the C-ADR-19 policy (any regulator order forces High), plus the sentence-level filter can't see "set aside" in the next sentence. This is a check-logic decision for CC-07 (C-ADR-26): whose order (issuer vs promoter or group), materiality, and current status. |

All Jio matches: regulator_order 2 fired / 5 blocked_soft; default_or_recall 1 fired / 1 blocked_soft. Minor: the severe scan starts at the `summary` section, so for Jio it scans from p.1 (the definitions are still skipped).

## (c) ARGON's L2 labels (`origin/p4/argon` @ 1cef042, 1,007 rows, all `label_source: ai`)
- **Neither Jio sentence is in L2.** Jio has 0 rows, which is correct: it's excluded and not in `splits.yaml`, so the hits export never read it.
- **The p.40 pattern is covered by close analogues:** `globe-civil-projects-2025` "No salary/dividend … in case of delay or default in repayment of facilities availed" is labelled `not_relevant`; `sanstar-2024` "In case of delay or default in repayment …" is `not_relevant`; and `stallion-india-fluorochemicals-2025`'s covenant list is `hypothetical`. So M3 trained on L2 should block p.40.
- **The p.472 pattern is labelled `actual_event`:** all 22 "SEBI … imposed penalty" rows and 10/11 "Adjudicating Officer passed an order" rows, e.g. `jsw-cement-2025` (dev) group company JSW Ispat and `bajaj-housing-finance-2024` "SEBI imposed a penalty of ₹50,000 on Bajaj Holdings". **So under the Phase 4 rule "force High only on `actual_event`", p.472 still forces High.** M3 can't remove it; G2's "0 false serious findings" needs an entity/materiality/status rule in CC-07.
