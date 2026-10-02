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
- Mobile workspace: the page header is tall, so the window scrolls as well as the panes (queued for the polish pass).
- ASR CER normalisation: skipped, `reviewed_by_akshat` is empty.

## Where to resume
- Next: F7 Model Lab, then F8 demo mode.

## RAM peak
- not yet measured
