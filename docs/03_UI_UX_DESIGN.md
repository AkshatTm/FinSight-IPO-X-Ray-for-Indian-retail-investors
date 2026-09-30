# 03 — UI/UX Design

**Goal:** someone who knows nothing about NLP should *see* FinSight work in 60 seconds: facts appear, a click lands on the exact words in the prospectus, a wrong number gets caught. The frontend is where the demo is won, so it gets the same care as the models.

---

## 1. Design concept: "Tick and tie"

Auditors verify a financial statement by *ticking and tying*: every figure gets a small pencil mark once it has been traced back to its source document. FinSight does exactly that, automatically, for a 500-page prospectus. The whole visual language comes from this:

- **The document is the hero.** Real prospectus pages are always visible; FinSight is an instrument laid over them, not a chatbot with a PDF attached.
- **Verification marks are the brand.** ✅ ⚠️ ❌ are drawn as auditor-style marks (a tick, a query mark, a cross) in fixed colours, and appear with the one deliberate animation in the product: the *tick-and-tie reveal*, where marks land one by one and a thin leader line briefly connects each number to its source.
- **Stamp-ink blue** (the violet-blue of Indian office rubber stamps) is the single brand accent: links, focus rings, the "source" highlight box on pages.
- **Quiet everywhere else.** No gradients, no decorative cards-in-cards, no motion that isn't answering a user action (except the one reveal).

Things we deliberately avoid (they read as generic templates): all-caps eyebrow labels, `A · B · C` meta strings, arrows appended to buttons, monospace for small labels, identical rounded cards with the same shadow everywhere, tinted near-black backgrounds.

---

## 2. Design tokens

### 2.1 Colour (define as CSS variables on `:root`; Tailwind reads them)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F5F7FA` (cool paper) | `#151A23` (ink slate) | App background |
| `--surface` | `#FFFFFF` | `#1C2330` | Panels |
| `--surface-2` | `#EDF0F5` | `#232C3B` | Hover, inset areas |
| `--rule` | `#D5DBE5` | `#2F394A` | Borders, dividers |
| `--text` | `#18202E` | `#E9ECF1` | Body text |
| `--text-muted` | `#5A6578` | `#98A2B3` | Secondary text |
| `--stamp` | `#4B4FD1` | `#8D90F2` | Brand accent, links, focus, source highlight |
| `--ok` | `#1B8A5A` | `#3CCB8B` | ✅ verified — **only** |
| `--query` | `#B7791F` | `#E9A84A` | ⚠️ unverifiable — **only** |
| `--bad` | `#C53030` | `#F07070` | ❌ contradicted — **only** |

Highlight boxes on page images: source = `--stamp` at 18 % fill + 1.5 px outline; evidence in drawers = verdict colour at 18 % fill. Page images always sit on white regardless of theme (they are paper).

The three verdict colours are reserved: no buttons, charts or decorations may use them. Charts use `--stamp` plus greys; the only exception is the verifier confusion matrix, which is *about* verdicts.

### 2.2 Typography

| Role | Face | Notes |
|---|---|---|
| UI and body (Latin) | **IBM Plex Sans** 400/500/600 | Corporate-financial character, excellent at small sizes |
| UI and body (Hindi) | **IBM Plex Sans Devanagari** 400/500/600 | Same design family, so bilingual screens feel like one product |
| Figures | IBM Plex Sans with `font-variant-numeric: tabular-nums` | Digits line up in cards and tables |
| Evidence comparisons | **IBM Plex Mono** | Only inside the evidence drawer's side-by-side values and the Inspector |

Load via `next/font/google`. Type scale (rem): 0.75 · 0.875 · 1 · 1.125 · 1.375 · 1.75 · 2.25 · 3. Body 1 rem / 1.55 line-height (Devanagari 1.7). Max line length ~72 characters in prose areas. Sentence case everywhere.

### 2.3 Space, shape, depth, motion

- 4 px grid; panel padding 16/20; card gap 12.
- Radius: 6 px on controls, 10 px on panels, 999 px on badges. Not everything gets the same radius.
- Depth by borders and surface steps, not shadows. One shadow token for floating layers only (popovers, drawers).
- Motion: 150–220 ms ease-out for user-triggered changes. The tick-and-tie reveal: marks appear 120 ms apart, leader line draws in 180 ms and fades after 900 ms. Respect `prefers-reduced-motion` (marks appear instantly, no leader line).

### 2.4 Indian number formatting (`lib/format.ts`, unit-tested)

- `formatINR(value, unit)` → `₹1,250.00 crore` · `₹12,500.00 million` · `₹1,25,000.00 lakh` · `₹12,50,00,00,000`.
- Indian digit grouping for full rupees; Western grouping for million/billion.
- Share counts: `1,23,45,678 equity shares`.
- Never round silently: show the precision the document used.

---

## 3. Information architecture

```
/                       Landing
/ipos                   Library
/ipos/[id]              Workspace  (X-Ray · Document · Chat; Inspector drawer; Glossary drawer)
/ipos/compare?a=&b=     Compare two IPOs (P2)
/lab                    Model Lab
/how-it-works           Interactive architecture
?demo=1                 Demo mode on any route
```

Global header: logo, Library, Model Lab, How it works, language toggle (EN / हिंदी), theme toggle, health dot (green = models loaded, amber = warming up).

---

## 4. Primary user flows

**Flow A — First look (Priya, 60 s)**
Landing → "Open a live X-Ray" → Workspace loads with X-Ray → she clicks *Fresh issue* → page 12 appears with the words boxed → she hovers the badge and sees "Matched on the cover page and in The Offer (p. 67)".

**Flow B — Ask and trust**
Suggested chip "What will they do with the money?" → streamed answer with `[1] [2]` → tick-and-tie reveal: 3 ✅ → she clicks `[2]` → viewer jumps to the Objects of the Offer table row.

**Flow C — The catch**
She types "Is the fresh issue ₹800 lakh?" → answer arrives → the number gets ❌ → evidence drawer opens: "Scale mismatch. You asked about ₹800 lakh (₹8 crore). The prospectus says ₹800 crore (p. 12). They differ by exactly 100×, the lakh-to-crore factor."

**Flow D — Hindi voice**
Taps mic → speaks "इस आईपीओ में प्रमोटर कौन हैं?" → transcript appears in the input (editable) → sends → Hindi answer with citations and marks.

**Flow E — Advice attempt**
"Should I apply?" → advice card: "FinSight explains what the prospectus says. It doesn't recommend whether to apply — that needs a SEBI-registered adviser. Here is what the prospectus says:" + 4 mini fact cards.

**Flow F — Examiner**
Model Lab → ladder table → per-field heatmap → click a cell → example predictions → "Inspect a live answer" → Inspector drawer with retrieval scores and checks.

---

## 5. Screens

### 5.1 Landing `/`

The hero is a real prospectus sentence, not a stat block. Layout (left-aligned, one column on phones):

```
┌───────────────────────────────────────────────────────────────┐
│ FinSight                                     Library  Lab  EN │
│                                                               │
│  Read the fine print.                                         │
│  All 500 pages of it.                                         │
│                                                               │
│  ┌─ a cropped RHP page image ────────────────────────────┐    │
│  │ "...Fresh Issue of up to [₹800.00 crore]✓ and an      │    │
│  │  Offer for Sale of up to [1,23,45,678] Equity..."     │    │
│  └───────────────────────────────────────────────────────┘    │
│   loop: a chatbot-style claim "₹800 lakh" gets ✗ with          │
│   "scale mismatch" — then corrected to ✓                      │
│                                                               │
│  [ Open a live X-Ray ]   How it works                         │
│                                                               │
│  {n} IPOs read · {pages} pages · seeded errors caught: {r}%    │  ← real numbers from eval_results only
│  Not investment advice. FinSight summarises public documents. │
└───────────────────────────────────────────────────────────────┘
```
(The `·` separators in this sketch become three separate stat blocks in the build.) Stats come from `eval_results/`; if a number isn't available yet, the block is hidden rather than faked.

### 5.2 Library `/ipos`
- Rows or cards (not identical boxes: company name large, a slim fresh-vs-OFS bar, issue size in tabular figures, listing date, sector).
- Search (company, sector), filters (year, issue size range), sort (listing date, size).
- Hover or focus: three key facts preview.
- Empty state: "No IPO matches 'xyz'. Clear filters."

### 5.3 IPO Workspace `/ipos/[id]` — the main screen

```
┌ header: Company name   Price band ₹440–463   Issue ₹1,250 cr   [EN|हिंदी] [Glossary] [Inspect] ┐
│ X-RAY (30%)             │ DOCUMENT (40%)                       │ CHAT (30%)                    │
│ The offer               │ ┌──────────────┐  thumbnails         │ suggested chips               │
│  Total issue   ₹1,250 cr✓│ │  page image  │  ▢ ▢ ▢ ▢           │ messages with [1] [2]         │
│  Fresh issue     ₹800 cr✓│ │  + highlight │                     │ faithfulness meter            │
│  OFS             ₹450 cr✓│ └──────────────┘                     │ [🎤] [ ask about this IPO…  ] │
│ People · Money use       │ section jump list · zoom · p. 12/612 │                               │
│ charts                   │                                      │                               │
└──────────────────────────┴──────────────────────────────────────┴───────────────────────────────┘
```
Panes are resizable (drag handles). Below 1024 px: tabs *X-Ray · Document · Chat*; clicking a source from X-Ray or Chat switches to the Document tab automatically.

**X-Ray panel**
- Groups: *The offer* (total, fresh, OFS, price band, face value), *People* (promoters, lead managers, registrar), *Money use* (objects of the offer).
- Fact row: label (EN or HI), value in tabular figures, verdict mark, page chip `p. 12`.
- Click row → viewer jumps + highlights (≤ 300 ms).
- Hover/focus → popover: source snippet with value highlighted, extractor used (Rules / Pretrained QA / Our model), confidence bar, consistency note ("Total = fresh + OFS ✓").
- **Unit toggle** (crore · million · lakh · ₹): all figures re-render instantly.
- **Issue composition** stacked bar: fresh vs OFS with %.
- **Use of proceeds** horizontal bars; click a bar → jumps to that table row.
- **Compare extractors** toggle: each row expands to show the three extractors' answers with ✓/✗ against gold where gold exists.
- ⚠️ rows show the reason inline ("Two different values found: ₹800 cr on p. 1, ₹80 cr on p. 67").

**Document viewer**
- Page WebP images with zoom (fit width / 100 % / 150 %), thumbnail strip, page input, section jump list.
- Highlight layer: absolutely positioned boxes from word bboxes scaled to the rendered size; animated outline on arrival (220 ms).
- `←/→` change pages. Prefetch ±3 pages and all pages referenced by the X-Ray.
- Find in document ◇ using word boxes.

**Chat panel**
- Suggested chips (EN + HI), including the scale-trick question.
- Stage line under the question: *Checking the question → Finding passages → Writing → Checking numbers* (driven by SSE `stage` events).
- Answer streams; `[n]` markers become citation chips after the `answer` event. Hover chip → passage preview; click → viewer jumps.
- **Tick-and-tie reveal** after the `verdict` events: each number is underlined, its mark lands, a leader line flicks toward the viewer if the evidence page is visible.
- Faithfulness meter: "3 of 4 figures verified".
- Click a mark → **Evidence drawer**:
  - Two columns in Plex Mono: *In the answer* vs *In the prospectus*, both normalized and shown in all units.
  - Reason in plain words (templates in §7).
  - Matched passage with the value highlighted; *Show in document* button.
- Abstain card (amber outline, not red): "This isn't in the prospectus as far as I can find. Closest passage: … (p. 214)".
- Advice card (neutral outline): refusal + SEBI note + 4 mini fact rows.
- Copy answer (citations become page numbers).

**Voice**
- Mic button: press to record, press to stop (no hold-to-talk; easier on laptops). Live level meter while recording; max 20 s.
- Transcript lands in the input box, editable, with "Heard in Hindi" tag; user presses Send.
- Hindi voice sets answer language to Hindi unless the toggle says otherwise.

**Inspector drawer** (the "Inspect" button; right side, 480 px)
- Stage timeline with ms per stage.
- Retrieval table: passage, page, BM25 rank, dense rank, fused rank, rerank score; dropped passages greyed below.
- Prompt sent to the LLM (collapsed).
- Checks table: number, normalized value, evidence value, rule, verdict.
- Fills live from SSE; also opens any past answer via `/api/traces/{id}`.

**Glossary drawer** (FR-19)
- Terms with EN and HI plain-language definitions (static, reviewed by Akshat): IPO, RHP vs DRHP, fresh issue, offer for sale, price band, face value, promoter, book running lead manager, registrar, anchor investor, lot size, objects of the offer, lakh/crore.
- Terms in X-Ray labels are dotted-underlined and open their entry.

### 5.4 Model Lab `/lab`
- Ladder table: extractor × (EM, token F1, normalized-value accuracy), mean ± std, n shown. BiLSTM-CRF row appears automatically when its JSON exists.
- Bar chart with error bars.
- Per-field heatmap (fields × extractors). Click a cell → 5 example predictions vs gold.
- Weak-label panel: examples generated, IPOs used, audit precision with 95 % CI.
- Verifier panel: P / R / F1 by error type + confusion matrix.
- Frontier comparison panel (P1): same questions, FinSight vs frontier model, with conditions stated.
- Extractor playground ◇ and numeral playground ◇.

### 5.5 How it works `/how-it-works`
Interactive SVG of the two pipelines. Hover a box → two-line explanation; click → opens a recorded Inspector example at that stage. Doubles as a slide.

### 5.6 Compare `/ipos/compare` (P2)
Two X-Rays side by side, same row order, differences highlighted in `--stamp`. Facts only, no "better/worse" language.

---

## 6. States

| State | Treatment |
|---|---|
| Loading | Skeletons shaped like the final content; never a full-page spinner |
| Empty | One sentence telling the user what to do next |
| Error | What happened + what to do ("The local model is still loading, about 20 seconds. Try again then.") |
| Cold start / warming | Health dot amber + banner "Models are warming up" with progress from `/api/health` |
| Degraded | Inspector and a subtle note: "Using keyword search only right now" |
| Offline backend | Banner; demo mode still works for scripted questions |

---

## 7. Microcopy

### 7.1 Verdict reasons (evidence drawer templates)
| Code | English | Hindi |
|---|---|---|
| `verified` | Matches the prospectus (p. {page}). | प्रॉस्पेक्टस से मेल खाता है (पृ. {page})। |
| `scale_mismatch` | Scale mismatch. The answer says {a}; the prospectus says {b} (p. {page}). They differ by exactly {factor}×, the {unit_a}-to-{unit_b} factor. | इकाई की गलती। उत्तर में {a} है; प्रॉस्पेक्टस में {b} है (पृ. {page})। दोनों में ठीक {factor} गुना का अंतर है। |
| `wrong_value` | Different figure. The prospectus says {b} for {metric} (p. {page}). | अलग आंकड़ा। प्रॉस्पेक्टस में {metric} के लिए {b} लिखा है (पृ. {page})। |
| `wrong_metric` | This figure belongs to {other_metric}, not {metric} (p. {page}). | यह आंकड़ा {metric} का नहीं, {other_metric} का है (पृ. {page})। |
| `not_found` | This figure doesn't appear in the passages used for this answer. | यह आंकड़ा इस उत्तर के स्रोत अंशों में नहीं मिला। |
| `placeholder` | The prospectus leaves this blank ([●]); it's decided later. | प्रॉस्पेक्टस में यह खाली ([●]) है; यह बाद में तय होगा। |

### 7.2 Key UI strings
| Key | English | हिंदी |
|---|---|---|
| verdict.ok | Verified | सत्यापित |
| verdict.query | Couldn't verify | पुष्टि नहीं हो सकी |
| verdict.bad | Doesn't match | मेल नहीं खाता |
| chat.placeholder | Ask about this IPO | इस IPO के बारे में पूछें |
| chat.listening | Listening… | सुन रहे हैं… |
| action.show_in_doc | Show in document | दस्तावेज़ में दिखाएँ |
| abstain.title | Not found in the prospectus | प्रॉस्पेक्टस में नहीं मिला |
| advice.title | FinSight doesn't give investment advice | FinSight निवेश सलाह नहीं देता |
| footer.disclaimer | Not investment advice. FinSight summarises public disclosures. | यह निवेश सलाह नहीं है। FinSight सार्वजनिक दस्तावेज़ों का सार देता है। |
| field.fresh_issue | Fresh issue | नया निर्गम (फ्रेश इश्यू) |
| field.ofs | Offer for sale | बिक्री के लिए प्रस्ताव (OFS) |
| field.price_band | Price band | मूल्य दायरा (प्राइस बैंड) |
| field.face_value | Face value | अंकित मूल्य (फेस वैल्यू) |
| field.promoters | Promoters | प्रवर्तक (प्रमोटर) |
| field.brlm | Book running lead managers | बुक रनिंग लीड मैनेजर |
| field.registrar | Registrar | रजिस्ट्रार |
| field.objects | Use of the money raised | जुटाई गई राशि का उपयोग |

Akshat reviews every Hindi string before the freeze (he's the native speaker; Claude Code drafts only).

---

## 8. Accessibility and responsiveness

- Every verdict = mark shape + word + colour. Contrast ≥ 4.5:1 for text in both themes.
- Full keyboard path: `/` focus chat, `Esc` close drawers, `←/→` pages, `Tab` through fact rows, `Enter` to jump to source, `⌘K`/`Ctrl K` palette ◇.
- Screen reader: fact rows are buttons with labels like "Fresh issue, ₹800 crore, verified, page 12".
- Layouts verified at 1366×768 (projector), 1920×1080, 390×844 (phone).
- `lang="hi"` on Hindi text nodes for correct shaping and screen readers.

---

## 9. Demo mode (`?demo=1` or `NEXT_PUBLIC_DEMO=1`)

- Chat uses the backend demo cache for scripted questions: real recorded SSE streams replayed with their original timing. Unscripted questions go live.
- Presenter hotkeys: `1` open demo IPO · `2` click Fresh issue · `3` ask the proceeds question · `4` ask the scale-trick question and open its ❌ drawer · `5` play the pre-recorded Hindi clip through the real ASR · `6` ask "Should I apply?" · `7` open Model Lab · `0` reset.
- A small step indicator in the bottom-left corner, hidden when not in demo mode.
- Honesty: demo mode never shows content the system didn't produce.

---

## 10. Frontend architecture notes

- Next.js App Router; server components for data pages, client components for interactive panes.
- Server state: TanStack Query. UI state: Zustand store `{activeIpo, activePage, highlight, language, unit, theme, inspectorOpen, glossaryOpen, demoStep}`.
- **One highlight mechanism:** anything with a source sets `highlight = {page, boxes, origin}`; the viewer reacts. X-Ray rows, citation chips, evidence drawers and proceeds bars all use it.
- SSE: `lib/sse.ts` parses `fetch` + `ReadableStream` (POST body supported).
- Types generated from the backend OpenAPI (`pnpm gen:api`) — never hand-written.
- MSW mocks + fixtures in `mocks/` so the UI is built before the backend exists (`NEXT_PUBLIC_USE_MOCKS=1`).

## 11. Component inventory

`AppShell`, `HealthDot`, `LanguageToggle`, `ThemeToggle`, `IpoList`, `IpoRow`, `IpoFilters`, `WorkspaceLayout`, `XRayPanel`, `FactRow`, `FactPopover`, `VerdictMark`, `UnitToggle`, `IssueCompositionBar`, `ProceedsChart`, `ExtractorCompare`, `PageViewer`, `HighlightLayer`, `ThumbnailStrip`, `SectionJumpList`, `ChatPanel`, `StageLine`, `MessageBubble`, `CitationChip`, `VerifiedNumber`, `EvidenceDrawer`, `FaithfulnessMeter`, `AbstainCard`, `AdviceCard`, `SuggestedChips`, `MicButton`, `InspectorDrawer`, `StageTimeline`, `RetrievalTable`, `GlossaryDrawer`, `LadderTable`, `LadderChart`, `FieldHeatmap`, `VerifierPanel`, `ColdStartBanner`, `DemoController`, `ExtractorPlayground` ◇, `NumeralPlayground` ◇, `CommandPalette` ◇.

## 12. Acceptance checklist (run before G4)

- [ ] Every document-derived figure is clickable and highlights its source within 300 ms
- [ ] No layout shift when marks appear (space reserved)
- [ ] Unit toggle changes every figure on screen, including chat answers' evidence
- [ ] Hindi UI strings reviewed by Akshat; Devanagari renders with Plex Sans Devanagari
- [ ] Loading, empty, error states exist for every async component
- [ ] Works at 1366×768 and on a phone
- [ ] `prefers-reduced-motion` disables the leader line and staggered reveal
- [ ] Playwright demo-flow test passes on mocks and on the real API
