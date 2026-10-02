# Morning report (overnight frontend run)

Updated after every merge. Plain language.

## Merged so far
- #67 Frontend spec added to the doc index; ASR references replaced by your read-aloud script.
- #69 Overnight setup (TODO and morning report files, skills ignored).
- #71 F1 scaffold: Next 16 app shell with CSS-glass nav, EN/HI, light/dark, mocks, number formatting and i18n tests, frontend CI.

- F2 Library page (this PR): search, sort, filter chips, fresh/OFS bar, hover preview, first-visit hint, empty/loading/error states, on mock data.

- F3 Workspace + Document (this PR): `/ipos/<id>` with resizable panes (>= 1280), two panes + tabs (1024-1279), three tabs below 1024; header with key facts and unit toggle; document viewer with doc switch, page input, zoom, section jump, thumbnails, keyboard, highlight box (store -> viewer in about 12 ms on mocks).

- F4 Facts panel (this PR): groups, fact rows with SVG verdict marks (shape + word + colour), source popover (sentence rebuilt from page words), unit toggle changes every amount, money split bar, use-of-money bars, pure-OFS and placeholder states, compare-extractors toggle, clicking a fact on a phone switches to the Document tab.

- F5 Ask (this PR): SSE client and parser (property-tested), reducer, seven mock streams (normal, scale trick, abstain, advice, forecast, privacy, error), stage line, tick-and-tie reveal (marks stagger 120 ms, space reserved, leader line when the cited page is on screen, reduced motion = instant), faithfulness meter, citation chips with preview, Copy toast, evidence drawer with the 13.1 reason templates, guard/abstain/error cards, composer (Enter, Shift+Enter, `/`, 300 limit). Measured layout shift while an answer streams: 0.008.

- F5b Voice, inspector, glossary, tour (this PR): mic button with MediaRecorder (20 s cap, level ring, timer, all eight states), transcript lands editable in the box and is never auto-sent, Hindi transcript switches the answer language; inspector drawer (steps and time, pages read incl. dropped, number checks, exact prompt from `/api/traces/{id}`); glossary drawer (17 terms, search) opened from the header, the advice card and the term popover; three-step first-visit tour (`fs_tour_workspace`, never in `?demo=1`); `?` shortcuts dialog. Composer drafts now live in the chat store.

- L Landing (this PR): all sections of spec 5 in EN and HI; hero lens over a stand-in cover page (CSS lens, solid box when reduced motion/transparency), tag after 400 ms, cursor-follow on mouse only; chatbot example card; three steps with marks; interactive mini demo on Ather (own highlight state, shared PageViewer); Hindi question with "Play the example" (hi_q02.m4a); limits; stats hidden when missing; final CTA. Glossary terms linked on first mention.

- H How it works, About, 404, 500 (this PR): two-row flow diagram (6 + 5 steps) with FAQ, About with limits and licences, not-found and error pages, all EN+HI.

- P3.6 chat orchestrator (this PR): `python -m finsight.chat ask --ipo <id> "<question>"` prints the real event stream (guard, retrieval, tokens, answer, verdicts, final); traces saved to SQLite; `forecast` guard reason; objects-of-the-offer retrieval fix with tests on Ather and Urban Company; E7 script written (full run not done). Backend tests: 1043 pass.

- P4.1 API (this PR): all 16 routes answer for real on the processed data (smoke-tested on Ather: X-Ray, 586 pages, words, suggested questions, Lab files). Health works without Ollama (reports `degraded`). `uv run poe api` serves it on :8000.

- G3 gate (this PR): docs/gates/G3.md, PASS with three caveats, evidence from live runs through the real API. v0.3.0 not tagged: yours to tag.

- F6 real API (this PR): whole frontend checked against the live API (real X-Ray, real pages, real chat answer with marks). Highlight boxes needed work: the pipeline stores no boxes, so the API finds them from the page text (ADR-052 addendum). Mobile overflow from long section names fixed.

- F7 Model Lab (this PR): /lab reads real eval_results through three new or extended routes (retrieval, asr, weaklabels with audit). Numbers match PROGRESS (rules 86% / 23%, fine-tuned 74% / 85%, verifier 100/100, 0 false alarms). Frontier section hidden until an E9 file exists.

- F8 demo mode and G4 (this PR): `?demo=1` then keys 1 to 7 (0 resets); e2e green on mocks and on the real API; docs/gates/G4.md PASS with caveats.

- P polish (this PR): phone workspace fits one screen, EvidenceDrawer on the shared Drawer, overflow and tap-target sweep over all routes.

## Look at first
- docs/screenshots/f6/: workspace-highlight.png, chat-real.png, inspector-real.png, landing-demo.png
- docs/gates/G3.md
- docs/screenshots/h/: how-desktop-light-en.png, about-mobile-dark-hi.png, 404-desktop-light-en.png
- docs/screenshots/l/: desktop-light-en-full.png, desktop-dark-hi-full.png, mobile-dark-hi-full.png, desktop-hero.png
- docs/screenshots/f5b/: inspector-1366.png, voice-recording-1366.png, voice-done-1366.png, glossary-1366.png, tour-1366.png, composer-mobile-hi-dark.png
- docs/screenshots/f1/: desktop-light-en.png, desktop-dark-hi.png, mobile-menu.png
- docs/screenshots/f5/: desktop-answer.png, desktop-evidence-drawer.png, desktop-advice.png, desktop-abstain.png, mobile-dark-hi-drawer.png
- docs/screenshots/f4/: desktop-popover.png, desktop-split-objects-compare.png, desktop-pure-ofs.png, mobile-dark-hi.png
- docs/screenshots/f3/: desktop-highlight.png, mid-light-en.png, mobile-dark-hi.png
- docs/screenshots/f2/: desktop-light-en.png, desktop-hover-preview.png, desktop-empty.png, mobile-dark-hi.png

## Failed or skipped
- Phone document toolbar is still three rows (design call, see AKSHAT_TODO).
- ASR CER normalisation: skipped, `reviewed_by_akshat` is empty.

## Where to resume
- Whole frontend run is done (F1 to F8, G3, G4, P). Left for you: review docs/AKSHAT_TODO.md, tag v0.3.0 and v0.4.0, record the demo cache with the full profile, and fill `reviewed_by_akshat` in data/gold/asr_references.csv so the ASR CER step can run.

## RAM peak
- Lowest free RAM seen: about 2.4 GB (while Ollama qwen3.5:2b recorded the demo cache with the API and dev server up). Never under the 1.5 GB floor. Ollama and the API were stopped after each use.


---

# Overnight run 2

Updated after every merge. Plain language. Tests were green (1060) at the start.

## Decisions applied
- ADR-050, 051, 052 accepted (marked in docs/09_DECISIONS.md). New proposals for you: ADR-053 (objects table leads the use-of-money answer), ADR-054 (stored boxes, source sentence, thumbnails, lab examples).
- Tags v0.3.0 (G3) and v0.4.0 (G4) created on the gate commits, with GitHub releases.
- impeccable detector: not downloaded, as you said.

## Merged so far
- #104 Use-of-money answers lead with the objects table (each purpose with amount and unit). Live with qwen3.5:2b: Ather, Groww, Lenskart list every amount and the verifier marks them all ✅; LG says the company gets no money (English; Hindi still says "not found": the 2B model is weak in Hindi). HDB, Meesho, Physicswallah, Tata Capital and Urban Company still produce prose with few or no checkable numbers: that is the model, not the retrieval.
- Demo cache (this PR): 78 real recorded streams for all 10 IPOs, `full` profile (qwen3.5:2b), committed on purpose (792 KB). Nothing edited by hand; money questions were re-recorded after the fix.
- #110 MuRIL advice classifier (trained on Kaggle, 3 seeds, best by validation F1). On the tiny held-out part (18 questions) it blocks 9/9 advice questions but also blocks 4/9 factual ones; the keyword guard blocks 9/9 and 0/9. **The keyword guard stays the default**; MuRIL is switchable in config. Read the intervals, not the point estimates.
- #111 Frontend and API: hero shows the real Ather RHP page 3 with a lens over the fresh-issue sentence; phone document toolbar in one row; separate "i" glossary buttons; Model Lab heatmap cells open up to five real examples; stored value boxes, exact source sentence per fact and `?w=160` thumbnails in the API; "Bid closed {date} (Prospectus p.n)" in the workspace header (all 10 dates read from the Prospectus cover and consistent with the listing dates).
- #113 BiLSTM-CRF as an optional fourth rung of the ladder (3 Kaggle seeds). It passes its dev gate against the trivial baseline but is clearly weaker than the fine-tuned QA model on the gold test set; reported as measured.
- #112 Landing section 5.7 shows the real recorded Lenskart Hindi answer (copied unchanged, caption says the Hindi is imperfect); the How-it-works steps link to a real built IPO. ADR-020 wording corrected: the Hindi fluency scores are Claude drafts, **pending your confirmation** (the earlier text said confirmed).

## Needs you (short version; full list in docs/AKSHAT_TODO.md, section Run 2)
- Confirm or edit the fluency scores in `data/gold/hindi_fluency_sheet_rated.csv` (ADR-020 is provisional until then).
- Review ADR-053 and ADR-054, and the new Hindi strings (`land.lang.cap`, `how.link.*`).

## Later merges
- #115 Deploy prep (not deployed): Dockerfile (API group only, CPU wheels), `generate/llama_cpp_backend.py`, `scripts/bundle_artifacts.py` (tested), Space README, Vercel config, env templates, `docs/DEPLOY_STEPS.md`, ADR-022 proposed. The Docker image was **not built**: Docker Desktop was off and free RAM was about 3 GB.
- #116 Evaluation: E7 on dev and test with `full` (qwen3.5:2b, one run). Numbers marked ✅: dev 52/68 (0.76), test 59/86 (0.69); ❌ 8 and 5, all of the kind "true number from the wrong place" or "million turned into crore". Most unanswerable questions still get a fluent answer (abstain or not found: 3 of 9 dev, 4 of 11 test). A first run had 6 errors, all Hinglish questions, a harness bug (fixed, rerun). NLI on name claims is near chance (30/54 dev, 67/126 test), so it stays off. Latency: dev_light 3.5 s median per answer, full 32 s (17 s of it in retrieval with the LLM resident, not investigated).
- #117 Report drafts (sections 3-8, 11), README with a generated results table, Part C and viva questions for run-2 modules, 48 route screenshots (1366 and 390, light/dark, EN/HI; no horizontal scroll anywhere; the only console error is the missing `/api/lab/frontier`, expected until E9 exists).

## Not done
- Docker image build (see above); anything needing an account (deploy).
- Full Playwright e2e re-run beyond the screenshot sweep (CI e2e passed on the PRs).
- Frontier comparison (E9), gold v2 (P5.1), glossary content (P5.6) are not part of run 2.
