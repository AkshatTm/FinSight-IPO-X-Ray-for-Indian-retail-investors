# Morning report (overnight frontend run)

Updated after every merge. Plain language.

## Merged so far
- #67 Frontend spec added to the doc index; ASR references replaced by your read-aloud script.
- #69 Overnight setup (TODO and morning report files, skills ignored).
- #71 F1 scaffold: Next 16 app shell with CSS-glass nav, EN/HI, light/dark, mocks, number formatting and i18n tests, frontend CI.

- F2 Library page (this PR): search, sort, filter chips, fresh/OFS bar, hover preview, first-visit hint, empty/loading/error states, on mock data.

- F3 Workspace + Document (this PR): `/ipos/<id>` with resizable panes (>= 1280), two panes + tabs (1024-1279), three tabs below 1024; header with key facts and unit toggle; document viewer with doc switch, page input, zoom, section jump, thumbnails, keyboard, highlight box (store -> viewer in about 12 ms on mocks).

- F4 Facts panel (this PR): groups, fact rows with SVG verdict marks (shape + word + colour), source popover (sentence rebuilt from page words), unit toggle changes every amount, money split bar, use-of-money bars, pure-OFS and placeholder states, compare-extractors toggle, clicking a fact on a phone switches to the Document tab.

## Look at first
- docs/screenshots/f1/: desktop-light-en.png, desktop-dark-hi.png, mobile-menu.png
- docs/screenshots/f4/: desktop-popover.png, desktop-split-objects-compare.png, desktop-pure-ofs.png, mobile-dark-hi.png
- docs/screenshots/f3/: desktop-highlight.png, mid-light-en.png, mobile-dark-hi.png
- docs/screenshots/f2/: desktop-light-en.png, desktop-hover-preview.png, desktop-empty.png, mobile-dark-hi.png

## Failed or skipped
- ASR CER normalisation: skipped, `reviewed_by_akshat` is empty.

## Where to resume
- Next: F5 Ask (chat on mock SSE).

## RAM peak
- not yet measured
