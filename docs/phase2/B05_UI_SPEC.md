# B05 — UI Specification and Copy (Big Phase 2)

**Precedence:** for anything new on screen, this file wins. For existing screens, `12_FRONTEND_SPEC.md` still applies except where changed here. Rule zero is unchanged: **use the copy verbatim**; missing copy follows `12_FRONTEND_SPEC.md` §1 and goes to `docs/AKSHAT_TODO.md`.

**Language:** the risk report (Overview risk level, Red flags, Risks, Compare) is **English only**. When the UI language is Hindi, these tabs show a small note at the top: "यह जोखिम रिपोर्ट अभी केवल अंग्रेज़ी में है।" `[HI review]` The rest of the UI stays bilingual.

**Colours:** Watch / Concern / OK statuses must **not** use the verdict colours (those stay reserved for number verification). Use the stamp-blue scale and neutral greys plus icons:
- OK: outline circle + "OK" (neutral grey)
- Watch: half-filled circle + "Watch" (stamp blue 60 %)
- Concern: filled circle + "Concern" (stamp blue 100 %, bold label)
- Not available: dashed circle + "Not available"
- Risk level: Low / Medium / High as a 3-step bar in stamp-blue shades; the active step labelled; never red/green.

---

## 1. Site map changes

```
/                      Landing (updated sections)
/upload                Upload (sign-in required to submit)
/reports/[doc_id]      Report for any document (uploaded or showcase) — replaces /ipos/[id] as the canonical URL; /ipos/[id] redirects
/ipos                  Library (showcase + "Recently analysed" public reports)
/me/uploads            My uploads (signed in)
/lab                   Model Lab (+ Phase 2 sections)
/how-it-works, /about  Updated copy
```
Nav: **Analyse a document** (primary button) · IPOs · How it works · Model Lab · About · Sign in / avatar menu (My uploads, Sign out).

## 2. Landing changes (keep everything from 12 §5 unless replaced)

**Hero (replace sub + buttons):**
- Headline (unchanged): Read the fine print. All 500 pages of it.
- Sub: **Upload any IPO offer document. FinSight finds the risks, explains them in plain English, and shows you the exact page each one came from.**
- Primary button: **Analyse an IPO document** → `/upload`
- Secondary: **Explore a sample report** → `/reports/<ather doc_id>`
- Small line: Free. Sign in with Google to upload. Runs on open-source models.

**New section after "How FinSight works": "What you get"** — four short blocks:
1. **The key facts.** Issue size, price, who is selling, what the money is for. Each linked to its page.
2. **Red flags.** 13 checks, like losses, cash burn, debt, and how cheaply insiders bought their shares. Each marked OK, Watch or Concern.
3. **Every risk, in plain English.** Companies list dozens of risks in legal language. FinSight rewrites each one in simple words and shows the unusual ones first.
4. **A risk level.** Low, Medium or High, compared with past Indian IPOs, with the reasons listed.

**Replace "What FinSight won't do" lines:**
- It won't tell you whether to apply or buy.
- It won't predict listing prices or profits.
- Its risk level describes what the document discloses. It is not a recommendation.
Paragraph (unchanged SEBI text).

**"Built in the open" stats:** add "risks explained" (count across showcase) and "past IPOs used for comparison" (389) — hidden if missing.

## 3. Upload page `/upload`

**Title:** Analyse an IPO document
**Sub:** Upload a Red Herring Prospectus, a draft (DRHP), or a final prospectus. FinSight reads it and builds a report in a few minutes.

**Drop zone:** "Drag a PDF here, or **choose a file**" · helper: "Up to 60 MB. Text PDFs only (not scans)."
**Where to find one (collapsible):** "Offer documents are public. You can find them on the SEBI website under Filings → Public Issues, or on the NSE and BSE IPO pages."
**Signed-out state:** drop zone visible but the button reads **Sign in with Google to upload**; line: "We ask you to sign in only to prevent misuse. We don't use your Google data for anything else."
**Limits line:** "You can analyse 3 documents a day."
**Consent line under the button (small):** "By uploading, you confirm this is a public offer document. Reports for public documents may be visible to anyone with the link."
**Duplicate:** if the SHA-256 already exists → immediately open the existing report with toast "This document was already analysed. Here's its report."

**Rejections (inline, after upload validation):**
| Reason | Copy |
|---|---|
| scanned | This PDF looks like a scan, so there's no text to read. Try the text version from the SEBI or exchange website. |
| password | This PDF is password-protected. Please upload an unlocked copy. |
| too_large | This file is larger than 60 MB. |
| too_many_pages | This document has more than 1,500 pages, which is more than FinSight can handle. |
| not_offer_document | This doesn't look like an IPO offer document. FinSight works with RHPs, DRHPs and prospectuses. |
| quota | You've reached today's limit of 3 documents. Try again tomorrow. |
| global_quota | FinSight has reached today's limit for everyone. Please try again tomorrow. |

## 4. Processing screen (shown at `/reports/[doc_id]` while `status = processing`)

Header: **Analysing {company or "your document"}** · sub: "You can leave this page. The report will be saved to My uploads."
Vertical stage list (each: icon, label, state, time):
| Stage | Label | Done text |
|---|---|---|
| detected | Checking the document | {Doc type badge} · {pages} pages |
| parsed | Reading every page | Read {pages} pages |
| sections | Finding the sections | Found {n} sections |
| facts | Pulling out the key facts | Key facts ready |
| financials + redflags | Running the red-flag checks | 13 checks done |
| risks_split + risks_scored | Finding every risk | Found {n} risks |
| risk_level | Working out the risk level | Risk level ready |
| simplify | Explaining risks in plain English | {done} of {total} explained |
| index | Preparing questions and answers | Ready for questions |

As soon as `facts` is done, a button appears: **See what's ready** (opens the report; remaining sections show skeletons with "Still working…").
Cold-start note (when the first simplification takes > 20 s): "Warming up the language model. The first one takes a little longer."
Failure of a stage: that row shows "Couldn't finish this step" + **Details** (plain reason) — the rest continues.
DRHP banner (after detection): "This is a draft (DRHP). Many amounts are still blank until the final prospectus, so some checks will say Not available."

## 5. Report page `/reports/[doc_id]`

### 5.1 Header (sticky)
Company name (h1) · doc type badge (RHP / DRHP / Prospectus) · sector (if known) · pages · "Analysed {date}" · buttons: **Share** (copies link) · **Download summary (PDF)** (P1, cuttable) · **Ask** (opens chat drawer).
Companion link if available: "Final prospectus also analysed → View".

### 5.2 Tabs
**Overview · Red flags · Risks · Compare · Facts · Document**
(Ask is a drawer available from every tab.) Mobile: tabs scroll horizontally.

### 5.3 Overview tab (default)
Order:
1. **Risk level card**
   - Title: **Risk level: {Low | Medium | High}**
   - Bar: Low · Medium · High with the active step marked.
   - Line: "More disclosed risk than {p}% of {n} past Indian IPOs." (percentile from B02 §7.4)
   - **Why:** up to 6 reasons, each "{label} · +{points}" linking to the red flag or risk.
   - **Disclaimer (always, cannot be hidden):** "This level summarises the risks this document discloses, compared with past Indian IPOs. It is not a recommendation to apply, buy or avoid, and it does not predict how the shares will perform."
   - Link: "How the risk level works" → modal (§6.3).
2. **Five things to know** — the top 5 risks by importance, each: plain-English sentence (or the title if not yet simplified) + category chip + "Read more" (opens the risk in the Risks tab).
3. **Red flags at a glance** — 13 compact status pills; click → Red flags tab anchored.
4. **The offer in one line** — "{Company} is raising ₹{fresh} crore for itself, and existing shareholders are selling ₹{ofs} crore. Price ₹{price} per share." (Variants: pure OFS → "The company receives none of the money: all ₹{ofs} crore goes to existing shareholders."; DRHP → "Amounts will be set in the final prospectus.")
5. Small footer line: "Every number links to its page. Numbers are checked by code, not by an AI model."

### 5.4 Red flags tab
**Title:** Red flags · **Sub:** 13 checks that beginners usually miss. Each one is calculated from the numbers in this document.
Filter chips: All · Concern · Watch · OK · Not available.
**Card per check** (order: Concern, Watch, OK, NA; within, by RF id):
- Status icon + **title** (from table below) + status word.
- One sentence (template below, filled with numbers + units as written).
- "Numbers used" (expandable): each value with doc + page chip.
- "How this check works" (expandable): the rule in plain words with thresholds.
- "Show in document" button.

| RF | Title | Sentence templates (OK / Watch / Concern / NA) |
|---|---|---|
| RF01 | Profit or loss | OK: "Profitable in each of the last 3 years (latest profit ₹{pat})." · Watch: "Made a loss of ₹{pat} in the latest year." · Concern: "Made a loss in each of the last 3 years (latest loss ₹{pat})." · NA: "FinSight couldn't find the profit figures." |
| RF02 | Cash from the business | OK: "The business brought in cash last year (₹{ocf})." · Watch: "The business used more cash than it brought in last year (₹{ocf})." · Concern: "The business has used more cash than it brought in for {k} of the last 3 years." |
| RF03 | Debt | OK: "Debt is {de}× its net worth." · Watch/Concern: "Debt is {de}× its net worth, which is high for a company like this." · NA (lender): "Not applicable: borrowing is a normal part of a lender's business." |
| RF04 | Who gets the IPO money | OK: "{fresh_pct}% of the money goes to the company." · Watch/Concern: "{ofs_pct}% of the money goes to existing shareholders who are selling, not to the company." |
| RF05 | What insiders paid | Watch/Concern: "Selling shareholders bought their shares at an average of ₹{waca}. The IPO price is ₹{price}, about {x}× more." · OK: "The IPO price is {x}× what selling shareholders paid on average." · NA: "Not available until the price is set." |
| RF06 | Founders' stake after the IPO | OK: "Promoters will still own {p}% of the company." · Watch/Concern: "Promoters will own only {p}% after the IPO." · Concern (no promoter): "This company has no identifiable promoter." |
| RF07 | Vague use of money | OK: "{g}% of the new money is for general or unspecified purposes." · Watch/Concern: "{g}% of the new money is for general purposes or acquisitions that aren't named yet." · NA (pure OFS): "Not applicable: the company receives no money from this IPO." |
| RF08 | Court cases | OK: "No criminal cases and the disputed amounts are small." · Watch: "There are {n} criminal case(s) involving the company, promoters or directors." · Concern: "Pending cases involve ₹{amt}, about {pct}% of the company's net worth." |
| RF09 | Dealings with related companies | OK/Watch/Concern: "Business with related parties was ₹{rpt}, about {pct}% of revenue." |
| RF10 | Dependence on a few customers | Watch/Concern: "The top customer brings in {t1}% of revenue{, and the top 10 bring in {t10}%}." · NA: "The document doesn't give customer shares." |
| RF11 | Price compared with listed peers | OK/Watch/Concern: "At the IPO price, the P/E is {pe}. The listed peers named in the document have a median P/E of {peer_pe}." · NA (loss): "Not applicable: P/E can't be calculated for a loss-making company." |
| RF12 | Auditor's remarks | OK: "No remarks from the auditor in the summary." · Watch: "The auditor drew attention to: {short}." · Concern: "The auditor gave a qualified opinion: {short}." |
| RF13 | Pledged promoter shares | OK: "No promoter shares are pledged." · Watch/Concern: "{pct}% of promoter shares are pledged as security for loans." |

### 5.5 Risks tab (the core)
**Title:** Every risk, in plain English · **Sub:** The company lists {n} risks. Here they are in simple words, with the most important first.
**Controls:** Sort: **Most important first** (default) · Order in document · By category. Category filter chips (10, with counts). Search box "Search risks". Toggle: **Show only unusual risks** (novelty < 10%).
**Risk card:**
- Top line: category chip · seriousness ("High / Medium / Low seriousness") · unusualness badge: "Unusual: in {x}% of past IPOs" when < 10%, "Common: in {x}% of past IPOs" when > 60%, otherwise "In {x}% of past IPOs".
- **Plain English:** the rewrite (≤ 60 words). If pending: skeleton + "Explaining…" (click → prioritised). If rejected: "A simple version isn't available for this one, so here is the original." + original shown.
- **Their wording** (collapsed): the original title in bold + body (scrollable, max 12 lines) + page chip.
- Notes (only when true):
  - Hedging flag: "Written cautiously, but this describes something that has already happened."
  - Numbers: "Contains figures: {list}" (each clickable to page).
- Similar risks in past IPOs (collapsed): up to 3 "{Company} ({year}): {title}".
- Buttons: **Show in document** · **Ask about this**.
- Card footnote (once per page, not per card): "Plain-English versions are written by FinSight's own model and checked: every number must match the original. Always read the original for anything important."

Category display names: financial → Money and profits; debt_liquidity → Debt and cash; customers_suppliers → Customers and suppliers; competition → Competition; legal_litigation → Court cases and legal; regulatory → Rules and regulators; promoters_governance → Promoters and management; operations → Operations; technology_data → Technology and data; market_macro → Economy and market.

### 5.6 Compare tab (P1, cuttable)
**Title:** How it compares · **Sub:** With the listed companies the document names as peers, and with {n} past Indian IPOs.
1. **Peers table:** Company · P/E · EPS (₹) · Return on net worth · Book value per share — issuer row highlighted; source chip "Basis for Offer Price, page {p}". Explainers in tooltips: P/E "Price divided by yearly profit per share. Higher means investors pay more for each rupee of profit."; RoNW "Profit as a share of the owners' money in the business."
2. **Against past IPOs:** horizontal percentile bars for issue size, OFS share, insider price gap, P/E (where available), each "Higher than {p}% of past IPOs".
Empty: "The document doesn't name listed peers." / "Not enough data to compare."

### 5.7 Facts and Document tabs
Existing X-Ray and viewer (Phase 1) unchanged, now fed by `doc_id`.

### 5.8 Ask drawer
Existing chat. New suggested chips on report pages: "What are the biggest risks?" · "Explain the risk level" · "How much do the promoters keep after the IPO?" · plus the existing chips. Guard: "Should I apply/buy?" → existing advice card + the risk level card (facts only).

## 6. Modals and shared copy

### 6.1 Sign-in modal
"Sign in to upload documents" · button **Continue with Google** · "We only use your email to keep track of your uploads and daily limit."

### 6.2 My uploads `/me/uploads`
Title: My uploads · table: Company · Type · Uploaded · Status (Processing / Ready / Partly ready / Failed) · Open. Empty: "You haven't uploaded anything yet." + **Analyse a document**.

### 6.3 "How the risk level works" modal
"FinSight adds up points from the red flags and the most serious unusual risks:
- Each Concern adds 2 points and each Watch adds 1.
- Each risk that is highly serious and appears in fewer than 10% of past IPOs adds 1 point (up to 4).
Then it compares the total with {n} past Indian IPOs. The lowest third is Low, the middle third is Medium, and the top third is High.
This tells you how much risk the document discloses compared with other IPOs. It does not tell you whether the shares will do well, and it is not advice."
Link: "See how well this matches past outcomes" → Model Lab §7.

### 6.4 Errors (add to 12 §13.5)
| code | Copy |
|---|---|
| upload_failed | The upload didn't finish. Check your connection and try again. |
| job_failed | Something went wrong while analysing this document. The parts that finished are shown. |
| unauthorized | Please sign in to do that. |
| not_found_report | We couldn't find that report. It may have been removed after 30 days. |

## 7. Model Lab additions `/lab` (each with "What this shows")
1. **Splitting risks** (E13) — "How often FinSight separates the risks correctly."
2. **Reading the financial checks** (E14, E15) — "How often the numbers behind the red flags are read correctly, and how often the status matches one worked out by hand."
3. **Sorting risks into categories** (E16) — ladder TF-IDF → base → large → teacher, macro-F1 with n.
4. **Plain-English rewrites** (E18–E20) — human faithfulness for 3 systems, readability drop, % rejected by checks. Honest line: "The rewrites are checked for numbers and certainty, not for every shade of meaning."
5. **Unusualness** (E22) — precision of "similar risk" at the chosen threshold.
6. **Does the risk level match what happened?** (E21) — scatter/box plot of outcome by level, ρ with CI, and the plain verdict sentence generated from the numbers ("weak", "moderate" or "no clear" relationship). This section must be shown even if the result is weak.
7. **Speed and cost** (E23–E24).

## 8. How it works / About updates
- How it works: add row 3 "Analysing an uploaded document": Upload → Check it's an offer document → Read and find sections → Red-flag checks → Find every risk → Compare each risk with 389 past IPOs → Rewrite in plain English and check the numbers → Risk level.
- About → Known limits: add "The risk level compares disclosures with past IPOs. It is not a prediction or a recommendation." and "Plain-English rewrites can miss nuance; the original is always one click away."

## 9. Acceptance (add to 12 §19)
- [ ] Risk-level disclaimer present on every view of the level, not dismissible.
- [ ] No forbidden words (B01 §6) anywhere in UI copy or rendered rewrites (automated test over i18n + a sample of rewrites).
- [ ] Status colours are not verdict colours.
- [ ] Every red flag and risk links to a page.
- [ ] Progressive loading works: report usable after `facts` with skeletons elsewhere.
- [ ] Upload flow works signed out → sign in → upload → processing → report, on mocks and on the real API.
