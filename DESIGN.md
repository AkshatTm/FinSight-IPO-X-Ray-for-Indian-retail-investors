# Design (seed for the impeccable skill; authority: docs/12_FRONTEND_SPEC.md, tokens in docs/03_UI_UX_DESIGN.md section 2)

**Concept:** tick and tie. Auditors mark a figure once they have traced it to its source; FinSight does that for a 500-page prospectus. The document is the hero; the UI is an instrument laid over it.

**Colour:** cool paper `#F5F7FA` / ink slate `#151A23`; one accent, stamp-ink blue `#4B4FD1` / `#8D90F2`; verdict colours (`--ok`, `--query`, `--bad`) only for verdict marks. Page images always sit on white.

**Type:** IBM Plex Sans + Plex Sans Devanagari, tabular figures; IBM Plex Mono only in the evidence comparison and Inspector. Scale 0.75 / 0.875 / 1 / 1.125 / 1.375 / 1.75 / 2.25 / 3 / 3.75 rem.

**Shape and depth:** radius 6 controls, 10 panels; borders and surface steps instead of shadows; one floating-layer shadow.

**Motion (emil-design-eng):** 160-200 ms, `cubic-bezier(0.23, 1, 0.32, 1)`, never `transition: all`, buttons scale 0.97 on press, no animation on frequent actions, one showpiece: the tick-and-tie reveal. Reduced motion: everything instant.

**Glass:** accent only, max 3 visible: nav bar (CSS glass), landing lens, mic button, demo step indicator (library). Solid fallback with a 1 px rule.

**Dials (taste v1):** app screens variance 4 / motion 3 / density 6; landing, how it works, about 6 / 4 / 3.
