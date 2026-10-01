# Akshat's to-do (collected during the overnight frontend run)

## Needs your decision
- (none yet)

## Hindi strings to review (`[HI review]` in docs/12_FRONTEND_SPEC.md, plus builder-drafted)
- Every `[HI review]` string in docs/12_FRONTEND_SPEC.md is used verbatim in frontend/lib/i18n.ts (nav, footer, library). Landing, Lab and About Hindi get added with their steps.

## New copy to review (strings the spec did not provide)
- Library: HI for the buttons/links the spec gave only in English: "Clear search" -> "खोज हटाएँ"; "Open Ather Energy" -> "Ather Energy खोलें"; filter group and sort labels (sr-only) "Sort" -> "क्रम".
- Keyboard shortcuts dialog (spec 17 asks for it, gives no copy): `keys.*` in frontend/lib/i18n.ts, EN and HI both drafted by the builder.
- Facts pane: Hindi tooltips for every field (spec 12 gave English only), `facts.chip` ("{doc} पन्ना {n}"), "Show fewer" / "+{n} और", "Details" label, `lib/content/fields.ts` and `facts.*`/`pop.*`/`split.*` in i18n.ts are builder drafts where the spec had no Hindi.
- Hindi unit words after amounts in the Hindi UI (`₹2,626.00 करोड़`): spec 15 only shows English; used करोड़ / मिलियन / लाख from the unit toggle labels.

## Data and evaluation
- `data/gold/asr_references.csv`: references are now the script you read aloud; `reviewed_by_akshat` is empty. Confirm them, then re-score ASR CER (ADR-021's 0.06 for turbo was measured on the old machine-drafted references).
- Rate `data/gold/hindi_fluency_sheet.csv`; review `advice_guard_set.csv` and `questions_*.jsonl` (from earlier PROGRESS entries).

## Backend notes the frontend found
- Thumbnails reuse the full page endpoint (`/pages/{n}`); a `?w=` or `/thumb` variant would cut payload. Decide in P4.1 (needs your review of the contract).

- The API X-Ray field has no source sentence. The popover rebuilds it from `/pages/{n}/words` around the field bbox. If P4.1 adds a `sentence` field it would be exact; for now it is derived.

- Chat: inline verdict marks show the icon with the word as tooltip and screen-reader text (spec 2.4 allows hiding the word only in dense tables; running text is treated the same). Say if you want the word printed beside each mark.
- Chat: `ask.*`, `ev.*`, `mark.open`, `cite.jump` strings and the HI forms of "In ₹ crore" / "In ₹ million" / "Reason" / "Source" are builder drafts.
- Guard reason: the contract lists `advice_intent | privacy` but the guard has forecast/rating/GMP categories (ADR-046). The UI maps any reason that is not privacy or forecast to the advice card; P3.6 should send `forecast` for the forecast rule.

## Skills and tooling notes
- impeccable's launcher (`scripts/impeccable`) downloads a self-contained binary on first run (SKILL.md Setup). I did not run it unattended; design process steps are followed from its reference/*.md instead. Say if you want the detector binary installed.
- Only humanizer ships a LICENSE (MIT). The other three skills have no licence file, so `.claude/skills/` is git-ignored; `skills-lock.json` (names, sources, hashes) is committed.
- Landing check (spec 5.11): ask a friend who has never heard of an RHP what FinSight does after the first three sections.
