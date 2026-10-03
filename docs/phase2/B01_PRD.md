# B01 — Product Requirements (Big Phase 2)

## 1. Summary

A beginner who is thinking about an Indian IPO uploads the offer document and, within minutes, sees:
1. **Key facts** (already built), with pages.
2. A **red-flag scorecard**: ~12 objective checks marked OK / Watch / Concern, each with one plain sentence and a page link.
3. A **risk level: Low / Medium / High**, with the reasons that produced it.
4. A **plain-English risk report**: every disclosed risk rewritten without legal language, sorted so the serious and unusual ones come first, original wording one click away.
5. **Comparisons** with the peers the document names and with ~389 past IPOs.
6. The existing **verified chat** (English/Hindi, voice) for anything else.

**Core promise:** *"In simple words: what could go wrong with this company, how unusual is that, and how much risk does the document itself disclose?"*

**Never:** "buy", "apply", "avoid", "good IPO", "bad IPO", price or listing predictions.

## 2. Users and jobs to be done

| Persona | Job | Must-have |
|---|---|---|
| **Priya, first-time IPO applicant** | "Before I apply, tell me what's risky about this company in words I understand." | Upload → risk level + top 5 risks in plain English in a few minutes |
| **Rahul, commerce student** | "Show me how the risks compare with other IPOs." | Unusualness, comparisons, original text |
| **Examiner** | "Prove the models work and are honest." | Model Lab results, validation of the risk level, limitations |
| **Recruiter** | "Is this a real product?" | Public URL, fast upload, polished UI, industry-grade docs |

## 3. User journeys

### J1 — Upload a new document (main journey)
1. Landing → **Analyse an IPO document** → `/upload`.
2. Sign in with Google (only required to upload).
3. Choose a PDF (≤ 60 MB, ≤ 1,500 pages). FinSight checks it's a text PDF and an offer document.
4. Progress screen with named stages. Results appear progressively:
   - ~1 min: document type, company name, key facts, page viewer.
   - ~2–3 min: red flags + risk level.
   - ~3–6 min: risk report fills in (most important first). Clicking a risk not yet simplified moves it to the front of the queue.
5. The report is saved; the user can share the link. If someone uploads the **same file again** (same SHA-256), the existing report opens instantly.

### J2 — Explore a showcase IPO (no login)
Library → any of the 10 showcase IPOs → the same report, precomputed.

### J3 — Ask about a risk
On a risk card: **Ask about this** → chat opens with the question prefilled ("Explain this risk: …"), answered from the document with verified numbers.

## 4. Features and requirements

IDs continue the Phase 1 scheme with a **B** prefix.

### B-FR-01 Upload any offer document (P0)
- Accept RHP, DRHP and final Prospectus PDFs from SEBI/NSE/BSE/company sites.
- **Document type detection** from the first pages ("Red Herring Prospectus", "Draft Red Herring Prospectus", "Prospectus"); shown as a badge. DRHP → banner: "This is a draft. Many amounts are still blank."
- Reject with a friendly message: scanned PDFs (too little text), password-protected PDFs, documents that aren't IPO offer documents (no matching cover/section structure), > 60 MB, > 1,500 pages.
- Google login required to upload; anyone can view a shared report link.
- Limits: 3 uploads per user per day, 30 per day overall (configurable); same-file dedupe by SHA-256.
- Progressive results (see J1) with live stage events.
- Target timings on the cloud GPU (p50): facts ≤ 90 s, red flags + risk level ≤ 3 min, all risks simplified ≤ 8 min for a 600-page RHP.

### B-FR-02 Red-flag scorecard (P0)
- ~12 checks (table in §5), each: status (OK / Watch / Concern / Not available), one plain sentence, the numbers used, doc + page link, "How this check works" tooltip.
- Thresholds live in `configs/redflags.yaml`, each with its explanation; tuned on dev IPOs only.
- Financial companies (banks, NBFCs, insurers) use sector-aware rules (e.g. leverage is normal for lenders).
- If a value can't be found: status **Not available** with "FinSight couldn't find this in the document" — never guessed.

### B-FR-03 Plain-English risk report (P0) — English only
- Split the Risk Factors section into individual risks (title + body).
- Per risk: category (10 categories), seriousness (High / Medium / Low), **unusualness** (share of past IPOs with a similar risk), hedge/softening flag, hard numbers found inside, plain-English rewrite (≤ 60 words), original text (expandable), page link.
- Default sort: "Most important first" = seriousness × unusualness. Other sorts: document order, category.
- Filters by category; search.
- Every number in a rewrite is checked by the verifier; a rewrite with a mismatched number is not shown (the original is shown with "Simplified version not available for this risk").
- "Ask about this" button (J3).

### B-FR-04 Risk level (P0)
- Low / Medium / High from a **transparent points system** over red flags and serious-unusual risks (B02 §7). Thresholds are set relative to the 389 past IPOs (e.g. Low = bottom third of past IPOs' points), so the level means "compared with past Indian IPOs".
- Always shows the reasons (each with its points and a link) and the fixed disclaimer (B05 §6.3).
- Validated against historical outcomes (B04 E21), results shown in the Model Lab whatever they are.

### B-FR-05 Comparisons (P1, first to cut)
- Peers: the "Basis for Offer Price" peer table (company, P/E, EPS, RoNW, NAV) next to the issuer, with plain explanations.
- Past IPOs: percentile bars vs the 389-IPO corpus for issue size, OFS share, fresh share, insider price gap, P/E where available.

### B-FR-06 Chat integration (P1)
- Chat can answer "What are the biggest risks?" using the risk report (risk cards become retrievable passages).
- Advice guard updated: questions about the risk level are allowed; "should I apply/buy?" still refused (with the risk level and reasons shown as facts).

### B-FR-07 Public deployment (P0)
- Public URL (Vercel) backed by Google Cloud Run; showcase IPOs instant; uploads processed on an L4 GPU that scales to zero.
- Cost guards: budget alert, max instances, per-user limits.

### B-FR-08 Industry-grade documentation (P0, B4)
- As defined in `B09_DOCUMENTATION_STANDARDS.md`.

## 5. Red-flag checks (initial definitions; thresholds tuned on dev IPOs only)

| ID | Check | Plain question it answers | Watch | Concern | Source section(s) |
|---|---|---|---|---|---|
| RF01 | Profit / loss trend | Is the business making money? | Loss in latest year | Loss in all of the last 3 years | Summary of financial information / restated financials |
| RF02 | Operating cash flow | Is cash coming in from the business? | Negative in latest year | Negative in 2+ of last 3 years | Restated cash flow statement |
| RF03 | Debt level (non-financial cos) | How much does it owe vs what it owns? | Debt/equity > 1.0 | > 2.0 | Restated balance sheet / capitalisation statement |
| RF04 | OFS share | How much of the IPO money goes to existing owners? | > 50 % | > 80 % | Cover / The Offer / Prospectus |
| RF05 | Insider price gap | Did sellers buy much cheaper than you pay? | Offer price ≥ 5× their average cost | ≥ 20× | "Weighted average cost of acquisition" in Summary of Offer Document |
| RF06 | Promoter stake after IPO | Do the founders still have skin in the game? | Promoter + group < 40 % | < 25 % or no identifiable promoter | Capital Structure / shareholding pattern |
| RF07 | Vague use of money | How much is "general purposes" or "unidentified acquisitions"? | > 20 % of fresh issue | ≥ 30 % | Objects of the Offer |
| RF08 | Court cases | Are there serious pending cases? | Any criminal case against company/promoters/directors | Total disputed amount > 10 % of net worth | Summary of outstanding litigation |
| RF09 | Related-party dealings | Business done with the promoters' own companies | > 10 % of revenue | > 25 % | Summary of related party transactions |
| RF10 | Customer concentration | Does a small group of customers keep it alive? | Top 10 > 50 % of revenue or top 1 > 20 % | Top 1 > 40 % | Risk factors / business section |
| RF11 | Price vs listed peers | Is the price high compared with similar listed companies? | P/E > 1.5× peer median | > 2.5× | Basis for Offer Price |
| RF12 | Auditor remarks | Did the auditor raise anything? | Emphasis of matter / CARO remark | Qualified opinion | Restated financials / auditor's report summary |
| RF13 | Pledged promoter shares | Are founders' shares pledged as loan security? | Any pledge | > 10 % of promoter holding | Capital Structure |

Not applicable cases (e.g. P/E for loss-making companies) → status "Not applicable" with the reason.

## 6. Wording rules (apply everywhere)

1. Allowed: "risk level", "Low / Medium / High", "Watch", "Concern", "the document discloses", "compared with past IPOs".
2. Forbidden in UI and model output: buy, sell, apply, avoid, invest (as an instruction), good/bad/strong/weak IPO, recommended, worth it, safe, guaranteed, listing gain, target price.
3. Every risk-level view carries the disclaimer (B05 §6.3).
4. Plain English: sentences ≤ 20 words where possible, no unexplained jargon; numbers keep the document's units.
5. Simplifications must not soften or exaggerate: same meaning, same numbers, same certainty ("may" stays "may"; "has happened" stays "has happened").

## 7. Non-functional requirements

| Area | Requirement |
|---|---|
| Speed (cloud, p50) | Showcase report < 1.5 s; upload → facts ≤ 90 s; → red flags + level ≤ 3 min; → all risks ≤ 8 min (600 pages) |
| Cost | ≤ ₹15 GPU cost per average upload; ₹0 idle; budget alert at ₹2,000/month |
| Reliability | Any stage can fail without losing earlier results; failed stages show "Couldn't do X" and the rest still renders |
| Security | Google login for uploads; per-user limits; PDFs parsed in an isolated job container with time/page limits; no secrets in the frontend |
| Privacy | No personal details of individuals shown (existing privacy guard + redaction apply to risks too); uploads deleted from storage after 30 days unless they're showcase |
| Accessibility | Same as Phase 1 (WCAG AA, keyboard, reduced motion) |
| Honesty | Outputs never hand-edited; limitations visible; AI-assisted labels disclosed |

## 8. Success metrics (targets; actuals reported either way)

| Metric | Target | Exp. |
|---|---|---|
| Risk splitting accuracy (risks correctly separated) | ≥ 90 % | E13 |
| Red-flag value extraction (NVM on gold v3) | ≥ 80 % | E14 |
| Red-flag status agreement with hand-computed status | ≥ 85 % | E15 |
| Category classifier macro-F1 (gold 150) | ≥ 0.75 | E16 |
| Simplification faithfulness (human, 50 rewrites) | ≥ 90 % "same meaning" | E18 |
| Readability gain (FKGL original → rewrite) | ≥ 4 grade levels lower | E19 |
| Numbers changed by simplifier (verifier) | 0 shown to users | E20 |
| Risk-level validation | Report correlation with outcomes, any result | E21 |
| Upload latency (p50, cloud) | per §7 | E23 |

## 9. Out of scope (Phase 2)

Buy/avoid recommendations; price or listing predictions; Hindi for the risk report; OCR of scanned PDFs; SME IPOs as showcase (uploads allowed but not optimised); debt offer documents; mobile apps; paid plans.

## 10. Open risks owned by Akshat

1. Teacher acceptance of the reframed project → update the pitch: "making Indian IPO risk disclosures understandable" (B08 B-ADR-09).
2. Risk level on a public site is advice-adjacent → transparent reasons + disclaimer; can be put behind a click if the teacher objects.
3. Cloud credits → budget alert and limits from day 1.
