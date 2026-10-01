# FinSight frontend — Claude Code instructions

Spec: `../docs/12_FRONTEND_SPEC.md` is the authority for everything on screen (copy verbatim, EN + HI in `lib/i18n.ts`). `../docs/03_UI_UX_DESIGN.md` §2 owns tokens. Backend contract: `../docs/06_API_CONTRACT.md` incl. the SSE event table.

## Commands
```
pnpm dev                          # :3000
NEXT_PUBLIC_USE_MOCKS=1 pnpm dev  # run on fixtures, no backend
pnpm lint · pnpm typecheck · pnpm test (Vitest) · pnpm test:e2e (Playwright) · pnpm build
pnpm gen:api                      # regenerate lib/api/types.ts from ../openapi.json
```

## Rules
- Plan (≤ 15 lines) before any task > ~50 lines; wait for approval (overnight run: plan goes in the PR body).
- TypeScript strict, no `any`. API types come only from `lib/api/types.ts` (generated) — never hand-written.
- Verdict colours (`--ok`, `--query`, `--bad`) are reserved for verification states. Every mark = shape + word + colour.
- All money/number formatting goes through `lib/format.ts` (Indian grouping, lakh/crore) and is unit-tested.
- One highlight mechanism: set `highlight` in the Zustand store; the viewer reacts.
- Every async component has loading, empty and error states. Skeletons, not page spinners.
- Server components for data pages; client components only where interactive.
- Keep components < ~200 lines; split when larger.
- Avoid generic template tells: no all-caps eyebrow labels, no `A · B · C` meta strings, no arrows appended to button text, no identical card grids with the same shadow.
- Respect `prefers-reduced-motion`. Test at 1366×768 and 390×844.
- Hindi strings live in `lib/i18n.ts`; Akshat reviews them. Set `lang="hi"` on Hindi nodes.
- Mocks are for development only; demo mode replays recorded real backend streams only.
- Don't read `node_modules/` or `.next/`.
- Next.js 16 / React 19: `params` and `searchParams` are Promises; use `LayoutProps`/`PageProps` helpers. Check `node_modules/next/dist/docs/` only for a specific API question.
- Glass (`liquid-glass-react`) only in the places spec 2.6 allows, max 3 visible; always through `components/glass/GlassSurface.tsx` (has the fallbacks).
