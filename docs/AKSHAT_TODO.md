# Akshat's to-do (collected during the overnight frontend run)

## Needs your decision
- (none yet)

## Hindi strings to review (`[HI review]` in docs/12_FRONTEND_SPEC.md, plus builder-drafted)
- (filled in as screens are built)

## New copy to review (strings the spec did not provide)
- (none yet)

## Data and evaluation
- `data/gold/asr_references.csv`: references are now the script you read aloud; `reviewed_by_akshat` is empty. Confirm them, then re-score ASR CER (ADR-021's 0.06 for turbo was measured on the old machine-drafted references).
- Rate `data/gold/hindi_fluency_sheet.csv`; review `advice_guard_set.csv` and `questions_*.jsonl` (from earlier PROGRESS entries).

## Skills and tooling notes
- impeccable's launcher (`scripts/impeccable`) downloads a self-contained binary on first run (SKILL.md Setup). I did not run it unattended; design process steps are followed from its reference/*.md instead. Say if you want the detector binary installed.
- Only humanizer ships a LICENSE (MIT). The other three skills have no licence file, so `.claude/skills/` is git-ignored; `skills-lock.json` (names, sources, hashes) is committed.
- Landing check (spec 5.11): ask a friend who has never heard of an RHP what FinSight does after the first three sections.
