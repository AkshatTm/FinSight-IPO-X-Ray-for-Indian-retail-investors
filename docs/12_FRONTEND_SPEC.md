# 12 — Frontend Specification (content, UX, copy, build order)

> **Big Phase 2:** new screens and all their copy are in `docs/phase2/B05_UI_SPEC.md`, which wins for anything new on screen; this spec still applies to existing screens except where B05 changes them (landing "won't" lines, `/reports/[doc_id]` replacing `/ipos/[id]`).

**Status:** authoritative for the frontend. Written by Claude (chat) for Akshat, 3 Oct 2026.
**Precedence:** for anything on screen (words, layout, states, order of sections) this document wins over `03_UI_UX_DESIGN.md`. For colours, tokens and the "tick and tie" concept, `03` still applies. For payload shapes, `06_API_CONTRACT.md` / `openapi.json` win.

**Rule zero for the builder:** use the copy in this document **verbatim**. You may fix a typo or shorten a line that does not fit, but do not rewrite tone, add adjectives, add exclamation marks, or invent new marketing lines. If copy is missing for something, write it following §1 and list it in `docs/AKSHAT_TODO.md` under "new copy to review".

`{curly}` = value from the API. `[HI review]` = Hindi string Akshat must check before freeze.

---

## Contents
1. Voice and writing rules
2. Visual system recap (tokens, type, motion, liquid glass, skills)
3. Site map and global chrome
4. Global states and components
5. Page: Landing `/`
6. Page: IPO Library `/ipos`
7. Page: IPO Workspace `/ipos/[id]` (X-Ray, Document, Chat, drawers, tour)
8. Page: Model Lab `/lab`
9. Page: How it works `/how-it-works`
10. Page: About and limits `/about`
11. 404 and error pages
12. Field display rules (all X-Ray fields)
13. Microcopy tables (verdicts, guard, abstain, errors, voice, stages)
14. Glossary content (EN + HI)
15. Number and date formatting
16. Demo mode
17. Accessibility and responsive rules
18. Build sequence with acceptance checks
19. Copy and design QA checklist

---

## 1. Voice and writing rules

FinSight talks like a calm, well-informed friend who has actually read the prospectus. Not a bank, not a hype app.

1. **Plain words first.** If a 17-year-old wouldn't understand a word, either replace it or link it to the glossary (dotted underline). Every finance term on the landing page is linked the first time it appears.
2. **Short sentences.** One idea per sentence. Most sentences under 20 words.
3. **Sentence case** everywhere (buttons, headings, labels). Never ALL CAPS except the literal acronyms IPO, RHP, OFS, SEBI.
4. **No hype.** Banned words: revolutionary, seamless, unlock, empower, leverage, cutting-edge, game-changer, effortless, magic, AI-powered (as a headline), supercharge, delve, robust, elevate. No exclamation marks. No emoji anywhere in the UI (the verdict marks are icons, not emoji).
5. **Say what it does, not what it is.** "Shows the page each number came from" beats "Transparent, citation-backed insights".
6. **Honest limits.** When FinSight can't do something, say it plainly: "I couldn't find this in the prospectus."
7. **Never advice.** No "good", "bad", "strong", "risky", "attractive", "worth" about an IPO. Facts only.
8. **Numbers are sacred.** Never round a document figure in copy. Always show the unit (₹ crore / ₹ million / shares).
9. **Hindi:** natural spoken Hindi (Devanagari), not literal translation. Keep common English finance words in Devanagari transliteration where people actually say them (आईपीओ, शेयर, फ्रेश इश्यू), with the English in brackets the first time on a page if helpful. Numbers always in Western digits (0–9). Company and person names stay in English script.
10. The **humanizer skill** runs over every English paragraph on Landing, How it works and About before merge. It must not touch numbers, field labels, legal lines or Hindi.

---

## 2. Visual system recap

### 2.1 Concept
"Tick and tie": auditors put a small mark next to every figure once they've traced it to the source. FinSight does that automatically. The document page is always the hero; the UI is an instrument laid over it.

### 2.2 Tokens
Use `03_UI_UX_DESIGN.md` §2 exactly (cool paper / ink slate, stamp-ink blue `--stamp`, reserved verdict colours `--ok` / `--query` / `--bad`). Verdict colours are used for nothing else.

### 2.3 Type
IBM Plex Sans + IBM Plex Sans Devanagari for UI and body, tabular figures for numbers, IBM Plex Mono only in the evidence comparison and the Inspector.

Scale (rem): 0.75 / 0.875 / 1 / 1.125 / 1.375 / 1.75 / 2.25 / 3 / 3.75 (3.75 only for the landing hero headline on desktop).

### 2.4 Verdict marks (icons, drawn as SVG, not emoji)
| State | Shape | Word (EN) | Word (HI) |
|---|---|---|---|
| verified | pencil-style tick | Matches | मेल खाता है |
| unverifiable | small "?" in a circle | Couldn't check | जाँच नहीं हो सकी |
| contradicted | pencil-style cross | Doesn't match | मेल नहीं खाता |
| placeholder (X-Ray only) | small dashed box | Blank in RHP | RHP में खाली |
Every mark always shows shape + word (word may be visually hidden only inside dense tables, but kept for screen readers).

### 2.5 Motion (emil-design-eng)
- Default UI transitions: 160–200 ms, `cubic-bezier(0.23, 1, 0.32, 1)` (ease-out). Never ease-in on UI. Never `transition: all`.
- Buttons: `:active` → `transform: scale(0.97)`.
- Drawers: slide 220 ms ease-out; close 160 ms.
- Things the user does many times (switching tabs, unit toggle, page turns): **no animation** beyond a 120 ms crossfade.
- **The one showpiece:** the tick-and-tie reveal in chat (§7.5.4).
- `prefers-reduced-motion`: all motion → instant, no leader lines.

### 2.6 Liquid glass (`liquid-glass-react`)
Accent only. Max **3** glass elements visible at once.

| Allowed | Not allowed |
|---|---|
| Landing hero lens (§5.2) | Document viewer surface |
| Top navigation bar | X-Ray values, chat text, verdict marks |
| Floating mic button | Tables, charts, drawers' content |
| Demo step indicator | Anything the user reads for more than 2 seconds |

Text on glass must pass 4.5:1 contrast in both themes. Fallback to a solid `--surface` with 1 px `--rule` border when: `prefers-reduced-transparency`, `prefers-reduced-motion`, non-Chromium browsers, or if the effect drops frames (test with Playwright trace). Lazy-load the library.

### 2.7 Skill roles
- **impeccable**: process (shape before a screen, critique + polish after, detector before merge). Seed its PRODUCT.md / DESIGN.md from `01_PRD.md`, `03_UI_UX_DESIGN.md` and this file.
- **taste (v1)**: dials: app screens DESIGN_VARIANCE 4 / MOTION_INTENSITY 3 / VISUAL_DENSITY 6; landing, how it works, about 6 / 4 / 3.
- **emil-design-eng**: every motion and interaction detail.
- **humanizer**: English prose on Landing, How it works, About, empty states.
Priority when they disagree: this file → `03` → impeccable → taste → emil.

---

## 3. Site map and global chrome

```
/                     Landing (for beginners)
/ipos                 IPO Library (start of the work area)
/ipos/[id]            Workspace: X-Ray · Document · Chat (+ drawers)
/lab                  Model Lab (results, for examiners and the curious)
/how-it-works         How it works (pipeline explained)
/about                About, data, limits, ethics
?demo=1               Demo mode on any route
```

### 3.1 Top navigation (glass bar, sticky)
Left: logo wordmark **FinSight** (stamp-blue tick inside the "i" dot is fine; no other decoration).
Centre/right links: **IPOs** · **How it works** · **Model Lab** · **About**
Right controls: language toggle `EN | हिंदी`, theme toggle (sun/moon icon, label "Theme" for screen readers), health dot.

Hindi nav: आईपीओ · यह कैसे काम करता है · मॉडल लैब · परिचय `[HI review]`

On the landing page only, add a primary button in the nav: **Try it** → `/ipos`.
Mobile (< 768 px): logo + language toggle + menu button; menu opens a sheet with the same links.

### 3.2 Health dot
| `/api/health.status` | Dot | Tooltip EN | Tooltip HI |
|---|---|---|---|
| ok | green-grey (use `--text-muted` ring + `--stamp` fill, NOT verdict green) | Everything is running | सब ठीक चल रहा है |
| warming | amber-grey pulse (stamp at 50 %) | Models are loading. This takes about 20 seconds the first time. | मॉडल लोड हो रहे हैं। पहली बार में लगभग 20 सेकंड लगते हैं। |
| degraded | outline only | Running with reduced features. {detail} | कुछ सुविधाएँ अभी सीमित हैं। {detail} |
| unreachable | hollow | Can't reach the FinSight server. Demo answers still work. | FinSight सर्वर से संपर्क नहीं हो पा रहा। डेमो उत्तर फिर भी काम करेंगे। |

(Health dot must not use verdict colours; they are reserved.)

### 3.3 Footer (all pages)
Line 1: **Not investment advice.** FinSight explains what public IPO documents say. It does not tell you whether to apply.
Line 2: Built by Akshat Tomar for CSE472 (Deep Learning for NLP), Lovely Professional University · Data: public SEBI filings · Source code on GitHub (link)
HI line 1: **यह निवेश सलाह नहीं है।** FinSight बताता है कि सार्वजनिक आईपीओ दस्तावेज़ों में क्या लिखा है। यह नहीं बताता कि आपको आवेदन करना चाहिए या नहीं। `[HI review]`

---

## 4. Global states and components

### 4.1 Cold-start banner (top of page, below nav, dismissible)
EN: **Getting ready.** The models are loading on this computer. Answers will start in about 20 seconds.
HI: **तैयारी हो रही है।** मॉडल इस कंप्यूटर पर लोड हो रहे हैं। लगभग 20 सेकंड में उत्तर मिलने लगेंगे।

### 4.2 Toasts (bottom-right, 4 s, max 1 at a time)
- Copied: "Answer copied with page numbers." / "पेज नंबर के साथ उत्तर कॉपी हो गया।"
- Link copied: "Link copied." / "लिंक कॉपी हो गया।"

### 4.3 Loading
Skeletons shaped like the final content. Never a full-page spinner. Skeleton shimmer off under reduced motion.

### 4.4 Generic error block (inside the failing panel, not full page)
Title: **Something went wrong here.** Body: {friendly message from §13.5}. Button: **Try again**.
HI: **यहाँ कुछ गड़बड़ हो गई।** · **फिर से कोशिश करें**

### 4.5 Glossary term component
Dotted underline in `--text-muted`. Hover/focus/tap → popover with the short definition from §14 and a link "More in the glossary" (opens the glossary drawer on that term). Works with keyboard (Enter opens, Esc closes).

---

## 5. Page: Landing `/`

**Goal:** a complete beginner understands, in under 60 seconds, what an IPO prospectus is, why it's hard, what FinSight does, and clicks "Try it on a real IPO".
**Layout:** single column, max width 1120 px, generous vertical spacing (taste dials 6/4/3). Sections separated by space and a thin rule, not by coloured blocks.

### 5.1 Section order
1. Hero
2. New to IPOs? (three plain facts)
3. Why not just ask a chatbot? (the lakh/crore example)
4. How FinSight works (3 steps)
5. See it on a real page (interactive mini demo)
6. Ask in English or Hindi
7. What FinSight won't do
8. Built in the open (real numbers)
9. Final call to action
10. Footer

### 5.2 Hero
**Eyebrow:** none (no eyebrow labels).
**Headline (EN):** Read the fine print. All 500 pages of it.
**Headline (HI):** बारीक़ शर्तें पढ़िए। पूरे 500 पन्ने। `[HI review]`
**Sub (EN):** FinSight reads an IPO's offer document for you, pulls out the numbers that matter, and shows you the exact page each one came from.
**Sub (HI):** FinSight आपके लिए आईपीओ का ऑफ़र दस्तावेज़ पढ़ता है, ज़रूरी आंकड़े निकालता है, और हर आंकड़ा किस पन्ने से आया है, वह भी दिखाता है। `[HI review]`
**Primary button:** Try it on a real IPO → `/ipos` · HI: किसी असली आईपीओ पर आज़माएँ
**Secondary link:** How it works → `/how-it-works` · HI: यह कैसे काम करता है
**Small line under buttons:** Free. No sign-up. Runs on open-source models. · HI: मुफ़्त। कोई साइन-अप नहीं। ओपन-सोर्स मॉडल पर चलता है।

**Visual (right side on desktop, below text on mobile): "the lens"**
- A real cover page image from one demo RHP (use Ather Energy RHP PDF page 3, rendered WebP), shown at ~70 % opacity on paper white, slightly rotated −1.5°.
- A **liquid glass lens** (rounded rectangle ~220×90 px) rests over the fresh-issue sentence. Inside the lens the text is magnified 1.15× and sharp.
- Next to the lens, a small tag appears 400 ms after load: verdict mark **Matches** + "Fresh issue · ₹26,260 million · page 3".
- On pointer devices the lens follows the cursor within the image bounds (elastic, emil timing), snapping back to the fresh-issue sentence on mouse leave. On touch devices it stays put.
- Reduced motion / no glass support: static image with a solid highlighted box and the same tag.
- Alt text: "Cover page of a Red Herring Prospectus with the fresh issue amount highlighted and marked as matching the document."

### 5.3 New to IPOs? Start here.
**Heading:** New to IPOs? Start here. · HI: आईपीओ में नए हैं? यहाँ से शुरू करें।
Three short blocks side by side (stacked on mobile), each with a small line icon (no illustrations of people):

1. **What is an IPO?**
   When a company sells its shares to the public for the first time, that's an IPO (initial public offering). Anyone with a demat account can apply for shares.
   HI: **आईपीओ क्या है?** जब कोई कंपनी पहली बार अपने शेयर आम लोगों को बेचती है, उसे आईपीओ कहते हैं। जिसके पास डीमैट खाता है, वह शेयरों के लिए आवेदन कर सकता है।
2. **What is the RHP?**
   Before the IPO opens, the company publishes a Red Herring Prospectus (RHP). It's the official document with the details: how much money is being raised, who is selling shares, and what the money will be used for.
   HI: **आरएचपी क्या है?** आईपीओ खुलने से पहले कंपनी रेड हेरिंग प्रॉस्पेक्टस (RHP) जारी करती है। यह आधिकारिक दस्तावेज़ है जिसमें पूरी जानकारी होती है: कितना पैसा जुटाया जा रहा है, कौन शेयर बेच रहा है, और पैसा किस काम में लगेगा।
3. **Why does nobody read it?**
   It's usually 500 to 1,000 pages of legal language. The important numbers are spread across the cover, the offer section and a few tables.
   HI: **इसे कोई पढ़ता क्यों नहीं?** यह आमतौर पर 500 से 1,000 पन्नों का कानूनी भाषा वाला दस्तावेज़ होता है। ज़रूरी आंकड़े कवर पेज, ऑफ़र वाले हिस्से और कुछ तालिकाओं में बिखरे होते हैं।

(The demo RHPs range from 502 to 1,083 pages; keep "500 to 1,000" accurate. If the Library's page counts change, update this line.)

Glossary links on first mention: IPO, demat account, RHP.

### 5.4 Why not just ask a chatbot?
**Heading:** Why not just ask a chatbot? · HI: किसी चैटबॉट से ही क्यों न पूछ लें?
**Body:** General chatbots can be helpful, but with Indian offer documents they often run into two problems. They can mix up lakh, crore and million, and they rarely show which page a number came from. When it's your money, "probably right" isn't good enough.
HI: आम चैटबॉट मददगार हो सकते हैं, पर भारतीय ऑफ़र दस्तावेज़ों के साथ अक्सर दो दिक्कतें आती हैं। वे लाख, करोड़ और मिलियन में गड़बड़ कर सकते हैं, और शायद ही बताते हैं कि आंकड़ा किस पन्ने से आया। जब बात आपके पैसे की हो, तो "शायद सही" काफ़ी नहीं है।

**Example card (static, two rows):**
| | |
|---|---|
| A typical chatbot answer | "The fresh issue is ₹800 lakh." |
| What the document says (page 3) | "₹800 crore" |
Below the card, a ❌ mark with: **Doesn't match.** ₹800 lakh is ₹8 crore. The document says ₹800 crore. That's 100 times more.
HI: **मेल नहीं खाता।** ₹800 लाख यानी ₹8 करोड़। दस्तावेज़ में ₹800 करोड़ लिखा है। यह 100 गुना ज़्यादा है।
Caption under card (small, muted): Illustrative example. FinSight's own comparison with general chatbots is in the Model Lab. · HI: यह एक उदाहरण है। आम चैटबॉट से FinSight की तुलना मॉडल लैब में है।
(If `/api/lab/frontier` has data, replace "Illustrative example." with "From our tests: general chatbots got {x} of {n} figures wrong on these IPOs." Never invent this number.)

### 5.5 How FinSight works
**Heading:** How FinSight works · HI: FinSight कैसे काम करता है
Three numbered steps, horizontal on desktop with a thin connecting line, vertical on mobile:

1. **It reads the whole document.** Every page, including the tables, from the RHP and the final prospectus.
   HI: **यह पूरा दस्तावेज़ पढ़ता है।** हर पन्ना, तालिकाओं समेत, आरएचपी और फ़ाइनल प्रॉस्पेक्टस दोनों से।
2. **It pulls out the key facts.** Issue size, price, who is selling, what the money is for. Each fact links to its page.
   HI: **यह मुख्य तथ्य निकालता है।** इश्यू का आकार, कीमत, कौन बेच रहा है, पैसा किस काम में लगेगा। हर तथ्य उसके पन्ने से जुड़ा होता है।
3. **It checks every number in its answers.** Ask a question, and each number in the reply gets a mark.
   HI: **यह अपने हर उत्तर का हर आंकड़ा जाँचता है।** सवाल पूछिए, और जवाब के हर आंकड़े पर एक निशान लगेगा।

Under step 3, the three marks in a row with one line each:
- ✓ **Matches** — the same number is in the document. · मेल खाता है — वही आंकड़ा दस्तावेज़ में है।
- ? **Couldn't check** — the number isn't in the pages used. · जाँच नहीं हो सकी — यह आंकड़ा इस्तेमाल किए गए पन्नों में नहीं है।
- ✗ **Doesn't match** — the document says something different. · मेल नहीं खाता — दस्तावेज़ में कुछ और लिखा है।

### 5.6 See it on a real page (interactive mini demo)
**Heading:** Try it here · HI: यहीं आज़माएँ
**Body:** Click a fact. FinSight jumps to the page and highlights where it came from.
HI: किसी तथ्य पर क्लिक करें। FinSight उस पन्ने पर जाकर दिखाएगा कि यह कहाँ से आया।
Component: a compact, read-only copy of the Workspace for the demo IPO (Ather Energy by default): 4 fact rows on the left (fresh issue, offer price, total issue, face value) and a small page viewer on the right. Clicking a row loads the page and draws the highlight. Data from the real API (fall back to mock fixtures if the API is down).
Link under it: Open the full workspace → `/ipos/ather-energy-2025` · HI: पूरा वर्कस्पेस खोलें

### 5.7 Ask in English or Hindi
**Heading:** Ask in English or Hindi · HI: अंग्रेज़ी या हिंदी में पूछें
**Body:** Type a question, or press the mic and ask in Hindi. You'll see the words FinSight heard before it answers, so you can fix them.
HI: सवाल लिखिए, या माइक दबाकर हिंदी में पूछिए। जवाब देने से पहले आपको दिखेगा कि FinSight ने क्या सुना, ताकि आप उसे ठीक कर सकें।
Visual: a static chat bubble pair:
- User (Hindi): लेंसकार्ट के प्रमोटर कौन हैं?
- FinSight: the real answer from the demo cache for that question, with its citation chips. If not available, show the question only with a "Play the example" button that plays `/demo/hi_q02.m4a`.

### 5.8 What FinSight won't do
**Heading:** What FinSight won't do · HI: FinSight क्या नहीं करेगा
Three lines with a small "no" icon:
- It won't tell you whether to apply. · यह नहीं बताएगा कि आपको आवेदन करना चाहिए या नहीं।
- It won't predict listing prices or profits. · यह लिस्टिंग कीमत या मुनाफ़े का अनुमान नहीं लगाएगा।
- It won't rate or rank IPOs. · यह आईपीओ को रेटिंग या रैंक नहीं देगा।  *(Phase 2: replaced by the three lines in `docs/phase2/B05_UI_SPEC.md` §2.)*
**Small paragraph:** In India, investment advice can only come from advisers registered with SEBI. FinSight sticks to what the documents say.
HI: भारत में निवेश सलाह केवल सेबी में पंजीकृत सलाहकार ही दे सकते हैं। FinSight केवल वही बताता है जो दस्तावेज़ों में लिखा है।
(Glossary link: SEBI.)

### 5.9 Built in the open
**Heading:** Built in the open · HI: खुले तरीके से बनाया गया
**Body:** Every number below comes from tests you can rerun from the source code.
HI: नीचे दिया हर आंकड़ा उन टेस्ट से आया है जिन्हें आप सोर्स कोड से दोबारा चला सकते हैं।
Four stat blocks (each hidden if its source value is missing):
| Stat | Source | Label EN | Label HI |
|---|---|---|---|
| `{n_ipos}` | `/api/ipos` length | IPOs read | आईपीओ पढ़े गए |
| `{n_pages}` | sum of `rhp_pages` (+ prospectus pages if exposed) | pages processed | पन्ने पढ़े गए |
| `{detection}%` | `/api/lab/verifier` overall detection | of planted number errors caught | जानबूझकर डाली गई गलतियों में से पकड़ी गईं |
| `{robust}%` | `/api/lab/ladder` fine-tuned body-only NVM | accuracy of our model when the cover page is hidden | कवर पेज छिपाने पर हमारे मॉडल की सटीकता |
Under the stats, two links: See the full results → `/lab` · Read the code on GitHub (external).

### 5.10 Final call to action
**Heading:** Pick an IPO and see what's inside. · HI: कोई आईपीओ चुनें और देखें कि उसमें क्या है।
**Button:** Browse IPOs → `/ipos` · HI: आईपीओ देखें

### 5.11 Landing acceptance checks
- [ ] A person who has never heard of an RHP can say what FinSight does after reading the first three sections (test by asking a friend; note it in AKSHAT_TODO).
- [ ] Every glossary term on first mention is linked.
- [ ] No hype words (§1.4), no exclamation marks, no emoji.
- [ ] Stats hide cleanly when a value is missing.
- [ ] Lens works with mouse, stays put on touch, falls back with reduced motion/transparency.
- [ ] Largest Contentful Paint under 2.5 s locally; no layout shift from the lens.

---

## 6. Page: IPO Library `/ipos`

**Goal:** choose an IPO quickly; understand at a glance how each offer is structured.

### 6.1 Header
**Title:** IPOs · HI: आईपीओ
**Sub:** {n} recent IPOs from the NSE and BSE. Pick one to see its facts, the original pages, and ask questions.
HI: एनएसई और बीएसई के {n} हाल के आईपीओ। किसी एक को चुनें, उसके तथ्य और मूल पन्ने देखें, और सवाल पूछें।

### 6.2 Controls
- Search input. Placeholder: "Search by company or sector" · "कंपनी या सेक्टर से खोजें"
- Sort select: Newest first (default) · Largest issue first · A to Z. HI: सबसे नए पहले · सबसे बड़ा इश्यू पहले · A से Z
- Filter chips: All · Has fresh issue · Only offer for sale. HI: सभी · फ्रेश इश्यू वाले · केवल ओएफएस

### 6.3 IPO row/card (list layout on desktop: rows, not identical boxes)
Each row shows:
- **Company name** (large), sector below in muted text.
- **Listed** {month YYYY} · HI: सूचीबद्ध {month YYYY}
- **Issue size** {total, in ₹ crore, tabular} (from Prospectus) · HI: इश्यू का आकार
- **Fresh vs OFS bar:** a slim two-part bar (stamp blue = fresh, grey = OFS) with labels "Fresh {x}%" and "OFS {y}%". For pure OFS show the full grey bar and the label "Only offer for sale". HI: "फ्रेश {x}%", "ओएफएस {y}%", "केवल बिक्री प्रस्ताव (ओएफएस)"
- **Pages:** {rhp_pages} pages · पन्ने
- Hover/focus preview (desktop): offer price, face value, number of lead managers.
- Whole row is a link to `/ipos/{id}`.

### 6.4 States
- Loading: 6 skeleton rows.
- Empty search: "No IPO matches "{query}". Try a company name like Lenskart." · "“{query}” से कोई आईपीओ नहीं मिला। Lenskart जैसा कंपनी का नाम आज़माएँ।" + **Clear search** button.
- Error: §4.4.

### 6.5 First-visit hint (dismissible, shown once, stored in localStorage key `fs_hint_library`)
"New here? Start with Ather Energy. It has a fresh issue and an offer for sale, so you'll see every kind of fact." · "पहली बार आए हैं? Ather Energy से शुरू करें। इसमें फ्रेश इश्यू और ओएफएस दोनों हैं, इसलिए आपको हर तरह के तथ्य दिखेंगे।" Link: Open Ather Energy.

---

## 7. Page: IPO Workspace `/ipos/[id]`

**Goal:** the main screen. Facts on the left, the real page in the middle, questions on the right.

### 7.1 Layout
Desktop ≥ 1280 px: three resizable panes 30 / 40 / 30 (min widths 300 / 420 / 320).
1024–1279 px: X-Ray and Chat share the right pane as tabs; Document stays left.
< 1024 px: tabs at the top: **Facts · Document · Ask** (HI: तथ्य · दस्तावेज़ · पूछें). Clicking any source in Facts/Ask switches to Document automatically and scrolls to the highlight.

### 7.2 Workspace header (sticky under nav)
- Back link: ← All IPOs · ← सभी आईपीओ
- **{Company}** (h1) + sector chip.
- Key facts strip (tabular): Offer price ₹{offer_price} · Issue size ₹{total} crore · Listed {date}. HI labels: ऑफ़र प्राइस · इश्यू का आकार · सूचीबद्ध.
- Right: **Glossary** button (book icon) · **Inspect** button (only enabled after an answer; tooltip "See how the last answer was made" / "देखें कि पिछला उत्तर कैसे बना") · Unit toggle (see 7.3.3).

### 7.3 Left pane: X-Ray ("Facts")
**Pane title:** Key facts · HI: मुख्य तथ्य
**Pane sub (muted, one line):** Click any fact to see it on the page. · किसी भी तथ्य पर क्लिक करें और उसे पन्ने पर देखें।

#### 7.3.1 Groups and order
1. **The offer** · ऑफ़र: Total issue size, Fresh issue, Offer for sale (shares), Offer for sale (amount), Offer price, Price band, Face value
2. **Money split** · पैसे का बँटवारा: issue composition bar (fresh vs OFS, from derived %)
3. **People** · लोग: Promoters, Book running lead managers, Registrar
4. **Use of the money** · पैसे का उपयोग: objects of the offer (bar list)
Field-specific labels, tooltips and empty texts: §12.

#### 7.3.2 Fact row anatomy
`[label + glossary underline]   [value, tabular]   [mark + word]   [doc chip "RHP p.3" / "Prospectus p.3"]`
- Click/Enter → set highlight (document switches to the right doc and page, box animates in).
- Hover/focus → popover:
  - "Found on {doc} page {page}" · "{doc} के पन्ना {page} पर मिला"
  - The source sentence with the value highlighted (stamp underline).
  - "Read by: Rules / Our fine-tuned model / Pretrained model" · "किसने पढ़ा: नियम / हमारा फ़ाइन-ट्यून मॉडल / प्रीट्रेंड मॉडल"
  - Confidence bar (only for model extractors), label "Confidence" · "भरोसा".
  - Checks, e.g. "Total = fresh issue + offer for sale ✓" · "कुल = फ्रेश इश्यू + ओएफएस ✓"
- List values (promoters, managers): show first 3, then "+{n} more" which expands inline.

#### 7.3.3 Unit toggle (header, applies everywhere incl. chat evidence)
Options: **₹ crore** (default) · **₹ million** · **₹ lakh** · **₹ (full)**. HI: ₹ करोड़ · ₹ मिलियन · ₹ लाख · ₹ (पूरा)
Tooltip: "Change how amounts are shown. The document's own wording is kept in the source view." · "रकम दिखाने का तरीका बदलें। दस्तावेज़ के मूल शब्द सोर्स में वैसे ही रहेंगे।"
No animation on switch (frequent action).

#### 7.3.4 Money split bar
Title: Where the money goes · पैसा किसके पास जाता है
Two segments: **To the company (fresh issue)** {x}% · **To selling shareholders (OFS)** {y}%. HI: **कंपनी को (फ्रेश इश्यू)** · **बेचने वाले शेयरधारकों को (ओएफएस)**
Helper line: "Only the fresh issue part goes to the company. The offer-for-sale part goes to the people selling their shares." · "केवल फ्रेश इश्यू वाला हिस्सा कंपनी को मिलता है। ओएफएस वाला हिस्सा शेयर बेचने वालों को जाता है।"
Pure OFS: full bar grey + "This IPO is only an offer for sale. The company receives none of the money." · "यह आईपीओ केवल बिक्री प्रस्ताव (ओएफएस) है। कंपनी को इसमें से कोई पैसा नहीं मिलता।"
If amounts are placeholders and no Prospectus figure exists: hide the bar and show "The split will be known once the final price is set." · "अंतिम कीमत तय होने पर बँटवारा पता चलेगा।"

#### 7.3.5 Use of the money (objects)
Horizontal bars, one per object, amount in the chosen unit, longest first; "[●] amount not set yet" rows at the bottom with a dashed bar. Click a bar → highlight that table row on the page.
Pure OFS: "Not applicable. The company receives no money from this IPO." · "लागू नहीं। इस आईपीओ से कंपनी को कोई पैसा नहीं मिलता।"

#### 7.3.6 Compare extractors (toggle at pane bottom)
Label: Show how each method read this · दिखाएँ कि हर तरीके ने इसे कैसे पढ़ा
When on, each fact row expands to three mini rows: Rules / Pretrained model / Our model, each with its value and ✓/✗ against gold (only for gold-labelled IPOs; otherwise no ✓/✗). Footnote: "Gold = values checked by hand against the PDF." · "गोल्ड = पीडीएफ़ से हाथ से जाँचे गए मान।"

### 7.4 Middle pane: Document
**Doc switch (segmented):** RHP · Final prospectus. HI: आरएचपी · फ़ाइनल प्रॉस्पेक्टस. Tooltip on RHP: "Published before the price was set. Some amounts are blank ([●])." · "कीमत तय होने से पहले जारी। कुछ रकम खाली ([●]) हैं।" Tooltip on Final prospectus: "Published after the price was set. Blanks are filled in." · "कीमत तय होने के बाद जारी। खाली जगहें भरी हुई हैं।"
(Use the API's companion-document info; if the API cannot address the prospectus pages yet, extend it per ADR, marked "needs Akshat review".)
**Toolbar:** page input "Page {n} of {total}" · पन्ना {n} / {total}; prev/next; zoom (Fit width · 100% · 150%); section jump menu "Jump to section" · "सेक्शन पर जाएँ" listing the found sections in plain names:
| Section id | EN | HI |
|---|---|---|
| cover | Cover page | कवर पेज |
| the_offer | The offer | ऑफ़र |
| capital_structure | Share capital | शेयर पूंजी |
| objects_of_the_offer | Use of the money | पैसे का उपयोग |
| promoters | Promoters | प्रमोटर |
| general_information | General information | सामान्य जानकारी |
**Thumbnails:** collapsible strip, off by default on < 1440 px.
**Highlight:** stamp-blue box, 1.5 px outline, 18 % fill, animates in (scale 0.98 → 1, 180 ms). Evidence highlights from chat use the verdict colour instead.
**Empty/placeholder page:** skeleton paper.
**Keyboard:** ← → pages; + − zoom.

### 7.5 Right pane: Ask (chat)
**Pane title:** Ask about {company} · {company} के बारे में पूछें

#### 7.5.1 Empty state
Text: "Ask anything about this IPO's documents. Each number in the answer will be checked against the pages." · "इस आईपीओ के दस्तावेज़ों के बारे में कुछ भी पूछें। जवाब का हर आंकड़ा पन्नों से जाँचा जाएगा।"
Suggested chips from `/api/ipos/{id}/suggested-questions` (show up to 6, mixed EN/HI). If the API returns none, use:
- How much money is the company raising? · कंपनी कितना पैसा जुटा रही है?
- What will the money be used for? · पैसा किस काम में लगेगा?
- Who are the promoters? · प्रमोटर कौन हैं?
- What was the final offer price? · अंतिम ऑफ़र प्राइस क्या था?
- Who is selling shares in the offer for sale? · ओएफएस में शेयर कौन बेच रहा है?

#### 7.5.2 Input
Placeholder: "Ask a question" · "सवाल पूछें". Send button "Ask" · "पूछें". `/` focuses the input. Enter sends, Shift+Enter new line. Max 300 characters; counter appears after 250.
Mic button (glass, floating at the right end of the input): see 7.5.6.

#### 7.5.3 Answer in progress: stage line
Under the user's question, a single line that updates:
| Stage | EN | HI |
|---|---|---|
| guard | Checking the question | सवाल जाँच रहे हैं |
| retrieving | Finding the right pages | सही पन्ने ढूँढ रहे हैं |
| generating | Writing the answer | जवाब लिख रहे हैं |
| verifying | Checking every number | हर आंकड़ा जाँच रहे हैं |
| done | (line disappears) | |
Show elapsed seconds after 5 s: "· {s}s".

#### 7.5.4 The tick-and-tie reveal (showpiece)
After `answer`, numbers in the text get a subtle underline. As each `verdict` event arrives, its mark appears next to the number: fade + scale from 0.9, 160 ms, staggered 120 ms apart. If the cited page is visible in the Document pane, a 1 px leader line in the verdict colour draws from the mark toward the page edge (180 ms) and fades after 900 ms. Space for marks is reserved from the start (no layout shift). Reduced motion: marks appear together, no line.

#### 7.5.5 Answer footer
- Faithfulness meter: "{v} of {n} numbers match the document" · "{n} में से {v} आंकड़े दस्तावेज़ से मेल खाते हैं". If n = 0: "No numbers to check in this answer." · "इस जवाब में जाँचने लायक कोई आंकड़ा नहीं है।"
- Citation chips `[1]` `[2]`: hover = passage preview (doc, page, 3 lines); click = jump + highlight.
- Actions: Copy · कॉपी करें; Inspect · जाँचें (opens Inspector for this answer).

#### 7.5.6 Voice
| State | Button label / text EN | HI |
|---|---|---|
| idle | Ask by voice (tooltip) | आवाज़ से पूछें |
| permission prompt | FinSight needs your microphone to hear the question. | सवाल सुनने के लिए FinSight को आपके माइक्रोफ़ोन की ज़रूरत है। |
| recording | Listening… tap to stop (+ live level meter, timer, max 20 s) | सुन रहे हैं… रोकने के लिए टैप करें |
| transcribing | Turning your voice into text. This takes about 10 seconds. | आपकी आवाज़ को टेक्स्ट में बदल रहे हैं। इसमें लगभग 10 सेकंड लगते हैं। |
| done | Heard in Hindi. Check the text, then press Ask. | हिंदी में सुना गया। टेक्स्ट जाँचें, फिर पूछें दबाएँ। |
| too long | That was longer than 20 seconds. Try a shorter question. | यह 20 सेकंड से लंबा था। छोटा सवाल आज़माएँ। |
| failed | Couldn't understand the audio. Try again in a quieter place, or type your question. | ऑडियो समझ नहीं आया। किसी शांत जगह से फिर कोशिश करें, या सवाल लिख दें। |
| mic blocked | Microphone access is blocked. You can allow it in your browser settings, or type instead. | माइक्रोफ़ोन की अनुमति बंद है। ब्राउज़र सेटिंग में इसे चालू करें, या सवाल लिख दें। |
The transcript is placed in the input box, editable, never auto-sent. When the transcript is in Hindi, the answer language switches to Hindi (unless the user changes the language toggle).

#### 7.5.7 Special answer cards (copy in §13.3–13.4)
- Abstain card (amber outline)
- Advice card (neutral outline) with key facts
- Privacy card (neutral outline)
- Forecast card (neutral outline)
- Error card (§13.5)

### 7.6 Evidence drawer (opens on clicking any verdict mark)
Right-side drawer, 440 px (full-screen sheet on mobile).
**Title:** by state: "This number matches" / "This number couldn't be checked" / "This number doesn't match". HI: "यह आंकड़ा मेल खाता है" / "इस आंकड़े की जाँच नहीं हो सकी" / "यह आंकड़ा मेल नहीं खाता"
**Comparison block (Plex Mono):**
| | In the answer | In the document |
|---|---|---|
| As written | {answer raw} | {doc raw} |
| In ₹ crore | … | … |
| In ₹ million | … | … |
HI column heads: जवाब में · दस्तावेज़ में · जैसा लिखा है
**Reason:** the template from §13.1 for the reason code.
**Source:** "{doc}, page {page}" + the passage (6 lines max) with the value highlighted.
**Button:** Show in document · दस्तावेज़ में दिखाएँ
**Footnote:** "FinSight compares numbers with code, not with another AI model." · "FinSight आंकड़ों की तुलना कोड से करता है, किसी दूसरे एआई मॉडल से नहीं।"

### 7.7 Inspector drawer ("Inspect")
**Title:** How this answer was made · यह जवाब कैसे बना
Sections (accordion, first two open):
1. **Steps and time** · चरण और समय: timeline guard → retrieve → generate → verify with ms each.
2. **Pages it read** · इसने कौन से पन्ने पढ़े: table: # · Document · Page · Section · Keyword rank · Meaning rank · Combined rank · Final score. Dropped passages greyed under "Considered but not used" · "देखे गए पर इस्तेमाल नहीं हुए". Column help (tooltips): Keyword rank = "How well the words match (BM25)"; Meaning rank = "How close the meaning is (embeddings)"; Final score = "Re-checked by a second model that reads question and page together".
3. **Number checks** · आंकड़ों की जाँच: table: number · as written · in ₹ · found in document · rule · result.
4. **Exact instructions sent to the model** · मॉडल को भेजे गए निर्देश: collapsed code block.
Empty: "Ask a question first. Then open this to see how the answer was made." · "पहले सवाल पूछें। फिर यहाँ देखें कि जवाब कैसे बना।"

### 7.8 Glossary drawer
Title: Glossary · शब्दकोश. Search box "Find a term" · "शब्द खोजें". Entries from §14 (EN or HI per toggle). Clicking a term in any underline opens the drawer scrolled to it.

### 7.9 First-visit tour (3 coach marks, once per browser, key `fs_tour_workspace`)
1. (on Facts pane) "These are the key facts from the offer document. Click one." · "ये ऑफ़र दस्तावेज़ के मुख्य तथ्य हैं। किसी एक पर क्लिक करें।"
2. (on Document pane) "This is the real page. The box shows exactly where the fact came from." · "यह असली पन्ना है। बॉक्स दिखाता है कि तथ्य ठीक कहाँ से आया।"
3. (on Ask pane) "Ask a question. Every number in the answer gets a mark." · "सवाल पूछें। जवाब के हर आंकड़े पर निशान लगेगा।"
Buttons: Next · आगे / Got it · समझ गया / Skip tour · टूर छोड़ें. Never shown in demo mode.

---

## 8. Page: Model Lab `/lab`

**Goal:** show the real results honestly, in plain words, with the technical detail one click deeper. Every chart has a "What this shows" line above it.
**Title:** Model Lab · मॉडल लैब
**Intro:** FinSight was tested on IPOs it never saw during training. These are the results, including where it falls short. · FinSight को उन आईपीओ पर जाँचा गया जो उसने ट्रेनिंग में कभी नहीं देखे। ये नतीजे हैं, उन जगहों समेत जहाँ यह कमज़ोर है।

### 8.1 Section: Reading the facts (the extractor ladder)
**What this shows:** Three ways of pulling facts out of a prospectus, scored against values checked by hand. · प्रॉस्पेक्टस से तथ्य निकालने के तीन तरीके, हाथ से जाँचे गए मानों के मुक़ाबले।
Table + bar chart with error bars. Columns: Method · Whole document · Cover page hidden · Tested on. Rows:
- **Rules** — hand-written patterns for the standard cover-page sentence. · नियम
- **Pretrained model** — a question-answering model (DeBERTa) used as it comes. · प्रीट्रेंड मॉडल
- **Our fine-tuned model** — the same model trained on about 4,000 examples FinSight labelled automatically. · हमारा फ़ाइन-ट्यून मॉडल
- (BiLSTM-CRF row appears automatically if its results exist.)
**Takeaway box (plain words, values filled from API):** "When the cover page is there, simple rules do best because the cover follows a fixed format. When the cover is hidden, the rules drop to {rules_body}% while our model stays at {ft_body}%. Training on automatic labels made the model {delta} points better than the pretrained version."
HI: "जब कवर पेज मौजूद होता है, तो साधारण नियम सबसे अच्छा करते हैं क्योंकि कवर एक तय ढाँचे में होता है। कवर छिपाने पर नियम {rules_body}% पर गिर जाते हैं, जबकि हमारा मॉडल {ft_body}% पर रहता है। अपने-आप बने लेबल पर ट्रेनिंग से मॉडल प्रीट्रेंड वर्ज़न से {delta} अंक बेहतर हुआ।" `[HI review]`
**Honesty note (muted):** "Small test set: {n} values from {k} IPOs. Treat differences of a few points as noise." · "छोटा टेस्ट सेट: {k} आईपीओ से {n} मान। कुछ अंकों के अंतर को संयोग मानें।"

### 8.2 Section: Fact by fact
**What this shows:** Which method gets each fact right. · कौन सा तरीका कौन सा तथ्य सही पढ़ता है।
Heatmap: fields × methods, cell = score, colour scale stamp-blue light→dark (not verdict colours). Click cell → 5 examples (value read vs value checked by hand).

### 8.3 Section: Automatic labels
**What this shows:** FinSight's model learned from examples labelled by a program, not by people. We checked a random 50 by hand. · FinSight का मॉडल उन उदाहरणों से सीखा जिन्हें किसी प्रोग्राम ने लेबल किया, इंसानों ने नहीं। हमने 50 बेतरतीब उदाहरण हाथ से जाँचे।
Stats: examples created · IPOs used · audit precision {p}% (95% range {lo}–{hi}%). Note: "Audit labels were drafted with AI help and reviewed by the author." · "ऑडिट लेबल एआई की मदद से बनाए गए और लेखक ने जाँचे।"

### 8.4 Section: Catching wrong numbers (the verifier)
**What this shows:** We planted wrong numbers in correct answers and checked how many FinSight caught. · हमने सही जवाबों में जानबूझकर गलत आंकड़े डाले और देखा कि FinSight ने कितने पकड़े।
Stats: caught {x}/{n} · false alarms {f}/{m} · unit mix-ups caught {35}/{40} on unseen IPOs ({40}/{40} after one rule fix). Confusion matrix by error type: wrong digit · wrong unit · wrong metric · invented number · harmless rounding.
Note: "This is a controlled test with planted errors. Real answers are harder." · "यह जानबूझकर डाली गई गलतियों वाला नियंत्रित टेस्ट है। असली जवाब ज़्यादा कठिन होते हैं।"

### 8.5 Section: Finding the right pages (retrieval) and answers
**What this shows:** How often the right page is among the five FinSight reads, and how its answers score. · कितनी बार सही पन्ना उन पाँच में होता है जिन्हें FinSight पढ़ता है, और इसके जवाब कितने सही हैं।
Stats: Recall@5 by method (keyword / meaning / combined / combined + re-check), answer numeric accuracy, abstention on unanswerable questions.

### 8.6 Section: Compared with general chatbots (only if `/api/lab/frontier` has data)
**What this shows:** The same questions given to a general chatbot with the full PDF. · वही सवाल, पूरी पीडीएफ़ के साथ, एक आम चैटबॉट से पूछे गए।
Table: metric · FinSight · general chatbot. Note listing conditions (date, model, interface). Say where the chatbot wins.

### 8.7 Section: Hindi
Stats: speech recognition character error {cer}% on {n} clips; answer quality notes. Honest line: "All the small open models we tried answer Hindi less fluently than English. The number checks still apply." · "हमने जितने छोटे ओपन मॉडल आज़माए, सभी हिंदी में अंग्रेज़ी जितने सहज नहीं हैं। आंकड़ों की जाँच फिर भी लागू होती है।"

### 8.8 Footer of the Lab
"Every number on this page is generated by scripts in the repository from the files in eval_results/." + link.

---

## 9. Page: How it works `/how-it-works`

**Title:** How FinSight works · FinSight कैसे काम करता है
**Intro:** Two parts. The first runs once per IPO and prepares everything. The second runs every time you ask a question. · दो हिस्से। पहला हर आईपीओ के लिए एक बार चलता है और सब कुछ तैयार करता है। दूसरा हर बार चलता है जब आप सवाल पूछते हैं।

Interactive SVG diagram (two rows). Each box: title + two lines; click = open a real example (a recorded trace or a screenshot).

**Row 1: Preparing an IPO (once)**
1. **Read the PDF** — Text and the position of every word on every page. · पीडीएफ़ पढ़ना — हर पन्ने का टेक्स्ट और हर शब्द की जगह।
2. **Find the sections** — The cover, the offer, share capital, use of money. · सेक्शन ढूँढना — कवर, ऑफ़र, शेयर पूंजी, पैसे का उपयोग।
3. **Read the tables** — Including the "₹ in million" note at the top. · तालिकाएँ पढ़ना — ऊपर लिखे "₹ मिलियन में" समेत।
4. **Pull out facts** — Rules for the fixed cover sentence; our trained model as a cross-check. · तथ्य निकालना — कवर के तय वाक्य के लिए नियम; जाँच के लिए हमारा ट्रेन किया मॉडल।
5. **Understand the numbers** — ₹800 crore and ₹8,000 million become the same value. · आंकड़े समझना — ₹800 करोड़ और ₹8,000 मिलियन एक ही मान बन जाते हैं।
6. **Index the pages** — So the right page can be found in a second later. · पन्नों का इंडेक्स — ताकि बाद में सही पन्ना पल भर में मिल जाए।

**Row 2: Answering a question (every time)**
1. **Check the question** — Refuse advice, predictions and personal details. · सवाल जाँचना — सलाह, अनुमान और निजी जानकारी के सवाल मना करना।
2. **Find the pages** — Keyword search and meaning search, then a second check. · पन्ने ढूँढना — शब्दों से खोज और अर्थ से खोज, फिर दूसरी जाँच।
3. **Write the answer** — A small open model running on this laptop, told to use only those pages. · जवाब लिखना — इसी लैपटॉप पर चलने वाला एक छोटा ओपन मॉडल, जिसे केवल उन्हीं पन्नों का इस्तेमाल करने को कहा गया है।
4. **Check every number** — Code compares each number with the pages. · हर आंकड़ा जाँचना — कोड हर आंकड़े की पन्नों से तुलना करता है।
5. **Show the marks** — Matches, couldn't check, or doesn't match. · निशान दिखाना — मेल खाता है, जाँच नहीं हो सकी, या मेल नहीं खाता।

Below the diagram, three short FAQ items:
- **Does it send my questions anywhere?** No. Everything runs on this computer with open-source models. (Deployed version: "on our server".) · क्या मेरे सवाल कहीं भेजे जाते हैं? नहीं। सब कुछ इसी कंप्यूटर पर ओपन-सोर्स मॉडल से चलता है।
- **Can it still be wrong?** Yes. The marks tell you which numbers were checked. Always look at the page for anything important. · क्या यह फिर भी गलत हो सकता है? हाँ। निशान बताते हैं कि कौन से आंकड़े जाँचे गए। किसी भी ज़रूरी बात के लिए पन्ना ज़रूर देखें।
- **Why doesn't it give advice?** Investment advice in India needs SEBI registration. FinSight only explains the documents. · यह सलाह क्यों नहीं देता? भारत में निवेश सलाह के लिए सेबी पंजीकरण ज़रूरी है। FinSight केवल दस्तावेज़ समझाता है।

---

## 10. Page: About and limits `/about`

**Title:** About FinSight · FinSight के बारे में
Sections (plain text, short):
1. **Who made it** — Akshat Tomar, B.Tech CSE, Lovely Professional University, as the course project for CSE472 Deep Learning for NLP (2026). Link to GitHub.
2. **What data it uses** — Public offer documents filed with SEBI for 10 IPOs from 2025, and a public research dataset of older IPO documents (Ghosh et al., CC BY-NC-SA 4.0) used only to train the fact-reading model.
3. **Known limits** (bullets, honest):
   - Covers 10 IPOs, not every IPO.
   - Scanned PDFs can't be read.
   - Hindi answers are less fluent than English ones.
   - The test sets are small, so scores can move a few points.
   - Some evaluation data was drafted with AI help and checked by the author.
4. **Not investment advice** — the SEBI paragraph from §5.8.
5. **Licences** — Code: MIT. Training data and the trained model: CC BY-NC-SA 4.0 (non-commercial).
Hindi versions for each paragraph `[HI review]` (builder may machine-draft these; they must be listed in AKSHAT_TODO.md).

---

## 11. 404 and error pages
**404:** Title "This page doesn't exist." · "यह पन्ना मौजूद नहीं है।" Body: "The link may be old. Try the IPO list." · "लिंक पुराना हो सकता है। आईपीओ सूची देखें।" Button: Browse IPOs.
**500:** Title "Something broke on our side." · "हमारी तरफ़ से कुछ गड़बड़ हो गई।" Body: "Reloading usually fixes it. If not, the demo pages still work." · "पेज रीलोड करने से अक्सर ठीक हो जाता है। नहीं तो डेमो पेज फिर भी काम करेंगे।" Button: Reload.

---

## 12. Field display rules

| field_id | Label EN | Label HI | Plain tooltip (EN) | Display | Placeholder text | Not in document |
|---|---|---|---|---|---|---|
| total_issue_size | Total issue size | कुल इश्यू का आकार | The total value of all shares offered in the IPO. | ₹ amount in chosen unit; source usually Prospectus | Set when the final price is fixed · अंतिम कीमत तय होने पर पता चलेगा | — |
| fresh_issue_size | Fresh issue | फ्रेश इश्यू | New shares created by the company. This money goes to the company. | ₹ amount | Amount blank in the RHP · आरएचपी में रकम खाली है | None. This IPO has no fresh issue. · कोई नहीं। इस आईपीओ में फ्रेश इश्यू नहीं है। |
| ofs_shares | Offer for sale (shares) | ओएफएस (शेयर) | Existing shares being sold by current owners. | count with Indian grouping + "shares" | Number of shares blank in the RHP · शेयरों की संख्या आरएचपी में खाली है | — |
| ofs_amount | Offer for sale (amount) | ओएफएस (रकम) | Money from the offer for sale. It goes to the sellers, not the company. | ₹ amount | Set when the final price is fixed · अंतिम कीमत तय होने पर पता चलेगा | — |
| offer_price | Final offer price | अंतिम ऑफ़र प्राइस | The price per share set at the end of bidding. | ₹ per share | Not set in the RHP · आरएचपी में तय नहीं | — |
| price_band | Price band | प्राइस बैंड | The price range for bids. It's announced separately, so the RHP leaves it blank. | ₹low – ₹high per share | Announced separately, blank in the RHP · अलग से घोषित, आरएचपी में खाली | — |
| face_value | Face value | फेस वैल्यू | A fixed accounting value per share. It is not the price you pay. | ₹ per share | — | — |
| promoters | Promoters | प्रमोटर | The people or companies that control the company. | list | — | — |
| book_running_lead_managers | Lead managers | लीड मैनेजर | Banks that run the IPO process for the company. | list | — | — |
| registrar | Registrar | रजिस्ट्रार | The firm that handles applications and share allotment. | text | — | — |
| objects_of_offer | Use of the money | पैसे का उपयोग | What the company says it will do with the fresh issue money. | bar list | Amount not set yet · रकम अभी तय नहीं | Not applicable. The company gets no money from this IPO. · लागू नहीं। इस आईपीओ से कंपनी को कोई पैसा नहीं मिलता। |
| fresh_share_pct / ofs_share_pct (derived) | Fresh / OFS share | फ्रेश / ओएफएस हिस्सा | Calculated by FinSight from the two amounts. | % with 1 decimal | hidden | hidden |

Placeholder rows show the dashed-box mark **Blank in RHP** and the doc chip pointing to the page with `[●]`. If the Prospectus has the value, show the Prospectus value with chip "Prospectus p.{n}" and a small note "Filled in the final prospectus" · "फ़ाइनल प्रॉस्पेक्टस में भरा गया".

---

## 13. Microcopy tables

### 13.1 Verdict reasons (evidence drawer)
| reason_code | EN | HI |
|---|---|---|
| verified | This number is in the document, for the same item, on {doc} page {page}. | यह आंकड़ा दस्तावेज़ में, इसी चीज़ के लिए, {doc} के पन्ना {page} पर है। |
| scale_mismatch | Wrong unit. The answer says {a} ({a_crore}). The document says {b} ({b_crore}). That's {factor} times different. | इकाई गलत है। जवाब में {a} ({a_crore}) है। दस्तावेज़ में {b} ({b_crore}) है। यह {factor} गुना का अंतर है। |
| wrong_value | Different number. For {metric}, the document says {b} on {doc} page {page}. | आंकड़ा अलग है। {metric} के लिए दस्तावेज़ में {doc} के पन्ना {page} पर {b} लिखा है। |
| wrong_metric | This number belongs to {other_metric}, not {metric}. | यह आंकड़ा {metric} का नहीं, {other_metric} का है। |
| not_found | This number doesn't appear in the pages used for this answer. It may still be correct, but FinSight couldn't confirm it. | यह आंकड़ा इस जवाब के लिए इस्तेमाल हुए पन्नों में नहीं है। यह सही हो सकता है, पर FinSight इसकी पुष्टि नहीं कर सका। |
| placeholder | The RHP leaves this blank ([●]). It's filled in later, in the final prospectus. | आरएचपी में यह खाली ([●]) है। यह बाद में फ़ाइनल प्रॉस्पेक्टस में भरा जाता है। |

### 13.2 Faithfulness meter wording
- all match: "{n} of {n} numbers match the document" (no colour celebration).
- some unchecked: "{v} of {n} numbers match. {u} couldn't be checked."
- any contradicted: "{c} number(s) don't match the document. Check the marked ones."
HI: "{n} में से {v} आंकड़े मेल खाते हैं। {u} की जाँच नहीं हो सकी।" · "{c} आंकड़े दस्तावेज़ से मेल नहीं खाते। निशान लगे आंकड़े देखें।"

### 13.3 Guard cards (reason from `guard` event)
**advice / rating / comparison / strategy / gmp**
Title: I can't tell you whether to invest. · मैं यह नहीं बता सकता कि निवेश करें या नहीं।
Body: In India, only advisers registered with SEBI can give investment advice. Here's what the documents say, so you can decide for yourself or ask an adviser. · भारत में केवल सेबी में पंजीकृत सलाहकार ही निवेश सलाह दे सकते हैं। दस्तावेज़ों में यह लिखा है, ताकि आप ख़ुद तय कर सकें या किसी सलाहकार से पूछ सकें।
Then 4 fact mini-rows from `facts` (label, value, doc chip). Link: "What is SEBI?" (glossary).
(Do NOT write "here are facts to weigh" or anything implying a decision.)

**forecast**
Title: I can't predict prices or profits. · मैं कीमत या मुनाफ़े का अनुमान नहीं लगा सकता।
Body: The documents describe the past and the plan, not the future. I can show what they say about past results or how the money will be used. · दस्तावेज़ बीते समय और योजना के बारे में बताते हैं, भविष्य के बारे में नहीं। मैं दिखा सकता हूँ कि पिछले नतीजों या पैसे के उपयोग के बारे में उनमें क्या लिखा है।
Buttons (chips): What will the money be used for? · Past revenue and profit (sends that question).

**privacy**
Title: I don't share personal details. · मैं निजी जानकारी नहीं देता।
Body: Offer documents list home addresses and contact details of some people. FinSight doesn't show them, even though they're public. I can tell you who the promoters and directors are and their roles. · ऑफ़र दस्तावेज़ों में कुछ लोगों के घर के पते और संपर्क जानकारी होती है। सार्वजनिक होने के बावजूद FinSight इन्हें नहीं दिखाता। मैं बता सकता हूँ कि प्रमोटर और डायरेक्टर कौन हैं और उनकी भूमिका क्या है।

### 13.4 Abstain card
Title: I couldn't find this in the documents. · यह मुझे दस्तावेज़ों में नहीं मिला।
Body: Rather than guess, FinSight only answers from the pages. The closest page it found is below. · अंदाज़ा लगाने के बजाय FinSight केवल पन्नों से जवाब देता है। सबसे क़रीबी पन्ना नीचे है।
Then: closest passage preview (doc, page) + "Show in document". Chips: "Try asking it differently" suggestions = the IPO's suggested questions.

### 13.5 Errors (by API error code)
| code | EN | HI |
|---|---|---|
| llm_unavailable | The answer model isn't running right now. Try again in a minute. Demo questions still work. | जवाब देने वाला मॉडल अभी नहीं चल रहा। एक मिनट बाद फिर कोशिश करें। डेमो सवाल फिर भी काम करेंगे। |
| models_warming_up | The models are still loading. This takes about 20 seconds the first time. | मॉडल अभी लोड हो रहे हैं। पहली बार में लगभग 20 सेकंड लगते हैं। |
| asr_failed | (voice "failed" text, §7.5.6) | |
| audio_too_long | (voice "too long" text) | |
| ipo_not_found | We couldn't find that IPO. | वह आईपीओ नहीं मिला। |
| page_out_of_range | That page isn't in this document. | वह पन्ना इस दस्तावेज़ में नहीं है। |
| rate_limited | Too many questions at once. Wait a few seconds. | एक साथ बहुत सारे सवाल। कुछ सेकंड रुकें। |
| validation_error | Something about that question didn't work. Try rephrasing it. | उस सवाल में कुछ गड़बड़ हुई। इसे दूसरे शब्दों में पूछें। |
| internal_error / unknown | Something went wrong on our side. Try again. | हमारी तरफ़ से कुछ गड़बड़ हुई। फिर से कोशिश करें। |
| network | Can't reach the FinSight server. Check that it's running. | FinSight सर्वर से संपर्क नहीं हो पा रहा। जाँचें कि यह चल रहा है। |

### 13.6 Language toggle behaviour
Switching EN/HI changes: all UI strings, field labels, glossary, and the language of the *next* answer. It does not re-translate past answers. Tooltip: "Changes the interface and the language of new answers." · "इंटरफ़ेस और नए जवाबों की भाषा बदलता है।"

---

## 14. Glossary content

Short definition (≤ 2 sentences) shown in popovers; long definition (≤ 4 sentences) in the drawer. Sync the backend `/api/glossary` source to this list.

| Term (EN / HI) | Short EN | Short HI `[HI review]` |
|---|---|---|
| IPO / आईपीओ | When a company sells shares to the public for the first time. | जब कोई कंपनी पहली बार आम लोगों को शेयर बेचती है। |
| Demat account / डीमैट खाता | An account that holds your shares electronically. You need one to apply in an IPO. | एक खाता जिसमें आपके शेयर इलेक्ट्रॉनिक रूप में रहते हैं। आईपीओ में आवेदन के लिए यह ज़रूरी है। |
| RHP (Red Herring Prospectus) / आरएचपी | The offer document filed before the IPO opens. The price and some amounts are left blank. | आईपीओ खुलने से पहले दाख़िल किया गया ऑफ़र दस्तावेज़। इसमें कीमत और कुछ रकम खाली छोड़ी जाती हैं। |
| Prospectus (final) / फ़ाइनल प्रॉस्पेक्टस | The version filed after the price is fixed, with the blanks filled in. | कीमत तय होने के बाद दाख़िल किया गया संस्करण, जिसमें खाली जगहें भरी होती हैं। |
| DRHP / डीआरएचपी | The first draft filed with SEBI for review, before the RHP. | आरएचपी से पहले सेबी को जाँच के लिए भेजा गया पहला मसौदा। |
| SEBI / सेबी | India's securities market regulator. It sets the rules for IPOs. | भारत का प्रतिभूति बाज़ार नियामक। यह आईपीओ के नियम तय करता है। |
| Fresh issue / फ्रेश इश्यू | New shares created by the company. The money goes to the company. | कंपनी द्वारा बनाए गए नए शेयर। पैसा कंपनी को मिलता है। |
| Offer for sale (OFS) / ओएफएस | Existing owners selling some of their shares. The money goes to them, not the company. | मौजूदा मालिक अपने कुछ शेयर बेचते हैं। पैसा उन्हें मिलता है, कंपनी को नहीं। |
| Price band / प्राइस बैंड | The range of prices within which you can bid. | कीमतों की वह सीमा जिसके भीतर आप बोली लगा सकते हैं। |
| Offer price / ऑफ़र प्राइस | The final price per share, set after bidding closes. | बोली बंद होने के बाद तय की गई प्रति शेयर अंतिम कीमत। |
| Face value / फेस वैल्यू | A fixed accounting value per share, like ₹1 or ₹10. It's not the price you pay. | प्रति शेयर एक तय लेखा मूल्य, जैसे ₹1 या ₹10। यह वह कीमत नहीं है जो आप देते हैं। |
| Promoter / प्रमोटर | The person or company that controls the company. | वह व्यक्ति या कंपनी जो कंपनी को नियंत्रित करती है। |
| Book running lead manager / बुक रनिंग लीड मैनेजर | A bank hired to manage the IPO. | आईपीओ संभालने के लिए नियुक्त बैंक। |
| Registrar / रजिस्ट्रार | The firm that processes applications and allots shares. | वह फ़र्म जो आवेदन संभालती है और शेयर आवंटित करती है। |
| Objects of the offer / ऑफ़र के उद्देश्य | What the company plans to do with the money from the fresh issue. | फ्रेश इश्यू से मिले पैसे से कंपनी क्या करने वाली है। |
| Lakh, crore, million / लाख, करोड़, मिलियन | 1 lakh = 1,00,000. 1 crore = 100 lakh. 1 million = 10 lakh. So ₹100 crore = ₹1,000 million. | 1 लाख = 1,00,000। 1 करोड़ = 100 लाख। 1 मिलियन = 10 लाख। यानी ₹100 करोड़ = ₹1,000 मिलियन। |
| [●] (blank) / [●] (खाली) | A blank in the RHP for a value that isn't decided yet, usually the price. | आरएचपी में किसी ऐसे मान के लिए खाली जगह जो अभी तय नहीं है, आमतौर पर कीमत। |
| GMP / जीएमपी | "Grey market premium": unofficial trading talk before listing. It's not in the documents and FinSight doesn't track it. | "ग्रे मार्केट प्रीमियम": लिस्टिंग से पहले की अनौपचारिक चर्चा। यह दस्तावेज़ों में नहीं होता और FinSight इसे ट्रैक नहीं करता। |

---

## 15. Number and date formatting (`lib/format.ts`, unit-tested)
- Crore: `₹2,626.00 crore` (Indian grouping for the integer part).
- Million: `₹26,260.00 million` (Western grouping).
- Lakh: `₹2,62,600.00 lakh`.
- Full: `₹26,26,00,00,000`.
- Shares: `11,051,746 shares` exactly as printed when shown "as written"; otherwise Indian grouping `1,10,51,746 shares` with a "shares" / "शेयर" suffix.
- Keep the document's precision (if it says `₹26,260 million`, "as written" shows that; the converted crore view shows `₹2,626.00 crore`).
- Percent: one decimal, `64.0%`.
- Dates: `12 Nov 2025` (EN), `12 नवंबर 2025` (HI). Months in Hindi: जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर.
- Digits always 0–9, also in Hindi UI.

---

## 16. Demo mode (`?demo=1`)
- Scripted questions are replayed from the backend demo cache (recorded real runs); everything else is live.
- Hotkeys: `1` open Ather Energy workspace · `2` click Fresh issue · `3` ask "What will the money be used for?" · `4` ask "Is the fresh issue ₹26,260 lakh?" and open its ❌ drawer · `5` play `/demo/hi_q02.m4a` through the real ASR · `6` ask "Should I apply for this IPO?" · `7` open Model Lab · `0` reset.
- Step indicator (glass) bottom-left: "Demo step {n} of 7 · press the next number". Hidden outside demo mode. No tour, no first-visit hints in demo mode.
- (Check the demo IPO in the cache matches; if the cache was recorded on another IPO, use that one and update this list in the PR.)

---

## 17. Accessibility and responsive rules
- WCAG 2.2 AA contrast; verdict = shape + word + colour.
- Full keyboard path: Tab order nav → Library rows → Workspace header → Facts → Document toolbar → Ask input. `/` focus input, `Esc` closes drawers/popovers, `←/→` pages, `?` opens a shortcuts dialog listing all keys.
- Screen reader names, e.g. fact row: "Fresh issue, 26,260 million rupees, matches, RHP page 3. Press Enter to show on page."
- `lang="hi"` on Hindi nodes.
- Breakpoints: 390 (phone), 768, 1024, 1280, 1440. Projector check at 1366×768.
- Touch targets ≥ 44 px. No hover-only information (popovers also open on focus/tap).

---

## 18. Build sequence with acceptance checks

Each step = one issue + branch + PR (rebase-merge). Before each screen: `impeccable shape`. After: impeccable critique + polish, emil review of motion, humanizer on English prose (Landing/How/About), Playwright screenshots at 1366×768 and 390×844 in light and dark → `docs/screenshots/<step>/`.

| # | Step | Main content | Done when |
|---|---|---|---|
| F1 | Scaffold | Next.js, TS strict, Tailwind, tokens from 03, fonts, shadcn, Zustand, TanStack Query, MSW + fixtures generated from openapi.json, AppShell with nav (glass) + footer, i18n dictionary (`lib/i18n.ts` with every string in this file), `lib/format.ts` + tests, liquid-glass wrapper with fallbacks, copy demo clip to `public/demo/` | build/lint/typecheck/vitest green; nav + footer render EN/HI; format tests pass |
| F2 | Library | §6 | search/sort/filter work on mocks; states present |
| F3 | Workspace + Document | §7.1, 7.2, 7.4 | highlight lands in < 300 ms; doc switch works; keyboard pages |
| F4 | Facts (X-Ray) | §7.3, §12 | every field state (present, placeholder, not in document, list, table) visible on mocks; unit toggle changes all numbers |
| F5 | Ask (chat) | §7.5, 7.6, §13 | 6 mock streams render correctly: normal, scale-trick, abstain, advice, forecast, privacy; tick-and-tie reveal; no layout shift |
| F5b | Voice, Inspector, Glossary, tour | §7.5.6, 7.7, 7.8, 7.9, §14 | voice states all reachable on mocks; inspector fills from mock trace |
| L | Landing | §5 | landing checklist §5.11 |
| H | How it works + About + 404/500 | §9, §10, §11 | diagram interactive; copy humanized |
| (backend) | P3.6 chat orchestrator, P4.1 API | per EXECUTION_PLAN + Objects-table fix | contract tests green; docs/gates/G3.md |
| F6 | Real API | switch off mocks, regenerate types, fix mismatches, cold-start banner, health dot | full flow on real API |
| F7 | Model Lab | §8 | every section reads real `/api/lab/*`; missing sections hide |
| F8 | Demo mode + E2E | §16; Playwright `e2e/demo-flow.spec.ts` runs hotkeys 1–7 | Playwright green on mocks and real API; docs/gates/G4.md |
| P | Polish pass | impeccable critique on every page, fix top issues | morning report lists before/after screenshots |

---

## 19. Copy and design QA checklist (run before every merge)
- [ ] Copy matches this file (diff the i18n dictionary against §5–§14).
- [ ] No banned words (§1.4), no "!", no emoji.
- [ ] Every finance term linked to the glossary on first use per page.
- [ ] Numbers show units; nothing rounded silently; digits 0–9 in Hindi.
- [ ] Verdict colours used only for verdicts; glass only in allowed places (≤ 3 visible).
- [ ] Loading, empty and error states exist for every async piece.
- [ ] Keyboard and screen-reader paths work; reduced motion and reduced transparency respected.
- [ ] Screenshots saved; no console errors in Playwright run.
- [ ] New Hindi strings added to AKSHAT_TODO.md for review.
