# Local app timings (smoke test, one run)

`uv run python scripts/smoke_local.py --fresh` on the laptop (RTX 2050 4 GB, 16 GB RAM, nothing
else running), Seshaasai Technologies RHP (562 pages, 12.9 MB; a train-slice IPO, not one of the
10 gold IPOs and not in the test or bench slices). Single run, so read them as typical, not exact.
A second document (Borana Weaves, 417 pages) took 351 s while the browser tests ran at the same
time; Glottis (11 MB) and GK Energy finished in the browser test in about 3.5 minutes.

| Step | Seconds (since upload) | Step took |
|---|---|---|
| checked the file | 1.1 | 1.1 |
| read every page (PyMuPDF) | 14.9 | 13.8 |
| sections, key facts, financials, red flags, compare | 21.4 | 6.5 |
| split the risks (78) | 34.6 | 13.2 |
| classify, novelty (bge-m3), seriousness | 102.4 | 67.8 |
| risk level, queue the 15 rewrites | 102.5 | 0.1 |
| page images, tables, search index (workspace ready) | 204.3 | 101.8 |
| **whole pipeline** | **204** | |
| first plain-English rewrite (background) | +5 after the click | |
| chat: fact question | first token 6.9, total 9.1 | |
| chat: red-flag question | first token 5.6, total 7.0 | |
| chat: "Should I apply?" (refused by the guard) | 0.0 | |

The first chat answer after a start is slower (30 to 60 s) while the reranker loads. The report
opens after about 21 seconds ("See what's ready"); the Facts and Document view opens when the last
step finishes.

Checks: 20 of 20 passed (API answers, pipeline finished, no failed step, 13 red flags, 78 risks
categorised with novelty, risk level with reasons, compare, 9 of 11 key facts, sections, page image
and words, suggested questions, a rewrite arrived, the fact and red-flag questions answered, the
advice question refused).
