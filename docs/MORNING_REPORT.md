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

## Look at first
- docs/screenshots/f1/: desktop-light-en.png, desktop-dark-hi.png, mobile-menu.png
- docs/screenshots/f5/: desktop-answer.png, desktop-evidence-drawer.png, desktop-advice.png, desktop-abstain.png, mobile-dark-hi-drawer.png
- docs/screenshots/f4/: desktop-popover.png, desktop-split-objects-compare.png, desktop-pure-ofs.png, mobile-dark-hi.png
- docs/screenshots/f3/: desktop-highlight.png, mid-light-en.png, mobile-dark-hi.png
- docs/screenshots/f2/: desktop-light-en.png, desktop-hover-preview.png, desktop-empty.png, mobile-dark-hi.png

## Failed or skipped
- Mobile workspace: the page header is tall, so the window scrolls as well as the panes (queued for the polish pass).
- ASR CER normalisation: skipped, `reviewed_by_akshat` is empty.

## Where to resume
- Next: F5b voice, inspector, glossary, tour.

## RAM peak
- not yet measured
