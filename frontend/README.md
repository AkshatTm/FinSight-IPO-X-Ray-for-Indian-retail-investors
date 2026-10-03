# FinSight web app

The FinSight website: landing page, IPO library, the workspace (fact sheet, document viewer and verified chat), Model Lab, uploads and the report page. It is built with Next.js (App Router), TypeScript in strict mode, Tailwind, TanStack Query and Zustand. The design spec is `docs/12_FRONTEND_SPEC.md` (Phase 1) and `docs/phase2/B05_UI_SPEC.md` (Phase 2).

## Run it

```bash
pnpm install
pnpm dev                          # http://localhost:3000, API at http://localhost:8000 (uv run poe api)
NEXT_PUBLIC_USE_MOCKS=1 pnpm dev  # no backend needed: every API call is answered by MSW mocks
```

## Scripts

| Script | What it does |
| --- | --- |
| `pnpm dev` / `pnpm build` / `pnpm start` | Next.js dev server, production build, production server |
| `pnpm lint` | ESLint |
| `pnpm typecheck` | Next route types, then `tsc --noEmit` |
| `pnpm test` / `pnpm test:watch` | Vitest unit and component tests |
| `pnpm test:e2e` | Playwright on the mocks (starts its own server on :3100) |
| `E2E_REAL=1 pnpm test:e2e` | Playwright against a running site (:3000) and API (:8000) |
| `pnpm gen:api` | Regenerate `lib/api/types.ts` from `../openapi.json` (never edit that file by hand) |

## Environment

Names only; `.env.example` lists them. No secret ever goes in the frontend.

| Variable | Meaning | When unset |
| --- | --- | --- |
| `FINSIGHT_API_ORIGIN` | Where Next.js rewrites `/api/*` (the Cloud Run API URL) | `http://localhost:8000` |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase project for Google sign-in | auth is "off": one local user |
| `NEXT_PUBLIC_USE_MOCKS` | `1` serves every API call from `mocks/` | the real API is called |

## Structure

| Folder | Holds |
| --- | --- |
| `app/` | Routes: `/`, `/ipos/[id]`, `/lab`, `/upload`, `/reports/[doc_id]`, `/me/uploads`, `/about`, `/how-it-works` |
| `components/` | One folder per screen (`workspace`, `facts`, `chat`, `reports`, `upload`, …) plus shared `ui` and `shell` |
| `lib/` | Pure logic with unit tests next to it (`report.ts` + `report.test.ts`), the API client and hooks (`lib/api`), and user-facing copy (`lib/content`, `lib/i18n.ts`) |
| `mocks/` | MSW handlers and fixtures; `report.ts` holds **synthetic** report data until it is regenerated from the fixture pack |
| `e2e/` | Playwright flows: demo, upload, report, and a real-backend workspace check |

## Rules

- Copy comes verbatim from the UI spec. Strings the spec does not give are marked "builder draft" in `lib/content/*` and listed in `docs/AKSHAT_TODO.md` for review.
- No investment advice: no buy, sell, apply or avoid wording (`configs/forbidden_phrases.yaml` is checked by a test). The risk level always shows its disclaimer.
- API types come only from `openapi.json` (`pnpm gen:api`). A change to the API contract changes `docs/phase2/B06_API_CONTRACT.md` in the same PR.
- Give new exported components and hooks a short TSDoc comment (B09 §7).
