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

- Inspector (7.7) and glossary drawer: Hindi for the three column tooltips (`insp.help.*`) and the glossary search placeholder / "no match" line are builder drafts; the glossary shows the 17-term short definitions only, since the spec has no long ones.
- Voice: mic opens a glass-style button in CSS mode (not the library) so the composer layout stays intact. Real ASR needs P4.1 `/api/voice`; the mock returns one Hindi sentence.
- Fact labels keep the dotted underline but do not open the glossary popover (a button inside the fact-row button is invalid HTML); the Glossary button and the advice card link open the drawer instead.

- Landing: hero image is a drawn stand-in (public/landing/rhp-cover.svg), not the real Ather RHP page 3 (I may not read PDFs). Replace it with a WebP of the real page if you want; the lens position constants are in components/landing/Hero.tsx. The lens is CSS glass, not liquid-glass-react (the library element positions itself fixed and cannot be pinned over an image), see ADR-050 note. Spec 5.7 asks for the real demo-cache answer under the Hindi question: not available until P4.1, so only the question and the play button show. The spec 5.11 friend test is yours: does a newcomer get it after the first three sections? The humanizer pass changed nothing on Landing because the spec copy is fixed verbatim. Landing stats "detection" and "robust" need `/api/lab/verifier` and `/api/lab/ladder` (P4.1); until then they are hidden outside mock mode.

- How it works: spec 9 says each box opens a real example (recorded trace or screenshot). None exists yet, so the boxes are static. Add them after P4.1 records the demo cache. About Hindi (spec 10 has English only) is a builder draft: every `about.*` string. Humanizer pass: no change, copy is fixed verbatim.

- Model Lab (F7): every `lab.*` Hindi string is a builder draft except none from the spec (the spec gives Hindi only for page-level lines); headings and column names the spec names only in English are mine. The spec asks for "5 examples per heatmap cell": the lab payload carries no examples, so the grid shows numbers only. E7 answer accuracy is not measured, the retrieval note says so. The frontier section (spec 8.6) is hidden: no E9 result file. Hindi section states that the ASR references are unreviewed.

## Data and evaluation
- X-Ray boxes: the extractors do not store a bbox for any value (found in F6). The API now locates boxes by matching text on the page (ADR-052), which is good for numbers and names but not for every list value. Consider storing the box in the extract stage in the next pipeline pass.
- `configs/ipo_meta.yaml` (sector and listing date for the 10 IPOs) was typed from memory of public listing dates: please verify each line.
- Demo cache: `data/demo_cache/` is empty until you run `ollama serve` and `uv run poe record-demo` (about 8 questions per IPO; slow on this laptop). The Landing page and demo mode (F8) use it.
- Approve or reject ADR-052 (page addressing, `not_available`, hand-entered sector/date).
- E7 (answers on dev questions through the real orchestrator): script is ready (`uv run python -m finsight.evaluate.answers --limit 20 --profile dev_light` with `ollama serve` running). I ran only one live smoke question (Ather, "How will the money be used?", qwen3.5:0.8b: right section, no numbers in the answer). The full run and the hand-check of `eval_results/e7_sample.jsonl` are not done.
- Approve or reject ADR-051 (`forecast` guard reason; objects-of-the-offer retrieval nudge).
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
