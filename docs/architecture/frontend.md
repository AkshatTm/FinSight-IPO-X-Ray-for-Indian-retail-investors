# Frontend

The web app is in `frontend/`: Next.js 16 (App Router), React 19, TypeScript in strict mode,
Tailwind CSS 4. Versions are pinned in `frontend/package.json`.

## Routes

| Route | File | Screen |
| --- | --- | --- |
| `/` | `app/page.tsx` | Home: hero with an animated reel (a made-up prospectus page is read, the total issue size is pulled out and checked), how it works, stats |
| `/ipos` | `app/ipos/page.tsx` | Library of the 10 showcase IPOs |
| `/ipos/[id]` | `app/ipos/[id]/page.tsx` | Workspace: facts, document pages, chat (`id` is an `ipo_id` or an upload's `doc_id`) |
| `/upload` | `app/upload/page.tsx` | Upload, model check, Analysing screen |
| `/reports/[doc_id]` | `app/reports/[doc_id]/page.tsx` | Report: Overview, Financials, Red flags, Risks, Compare |
| `/me/uploads` | `app/me/uploads/page.tsx` | My uploads |
| `/lab` | `app/lab/page.tsx` | Model Lab |
| `/how-it-works`, `/about` | `app/how-it-works`, `app/about` | Static pages |

## Data

- **API client** (`lib/api/client.ts`): every call goes to `/api/*`, which `next.config.ts` rewrites to
  `FINSIGHT_API_ORIGIN` (default `http://localhost:8000`).
- **Types** (`lib/api/types.ts`) are generated from the committed `openapi.json` with `pnpm gen:api`
  (openapi-typescript); never edited by hand. CI checks that `openapi.json` matches the API.
- **Server state** uses TanStack Query hooks (`lib/api/hooks.ts`), one query key per resource.
- **Client state** uses small Zustand stores (`lib/store.ts`, `lib/chatStore.ts`): unit choice, panes,
  chat turns.
- **Streams**: the Analysing page and the chat read server-sent events (`lib/sse.ts`, `lib/jobs.ts`,
  `lib/chat.ts`), resuming with `Last-Event-ID`.

## Mocks

With `NEXT_PUBLIC_USE_MOCKS=1`, Mock Service Worker answers every API call from `frontend/mocks/`
(`handlers.ts` plus fixtures for IPOs, X-Ray, chat, uploads, report, SOD and lab). The mock data is
synthetic ("Acme Speciality Chemicals"). The rewrites are switched off in that mode. Vitest component
tests and the default Playwright run use the same mocks.

## Design tokens

Colours, shadows and easing are CSS variables in `frontend/app/globals.css`, with a light and a dark set
("Charcoal & Saffron"):

| Token | Light | Use |
| --- | --- | --- |
| `--bg`, `--surface` | `#faf8f4`, `#ffffff` | page and card backgrounds |
| `--text`, `--text-muted` | `#1a1a1a`, `#6b6459` | body text |
| `--stamp` | `#e2591b` | saffron accent: primary buttons, active tab, charts |
| `--band`, `--on-band` | `#17161a`, `#f5f1ea` | charcoal hero band |
| `--ok`, `--query`, `--bad` | `#1f8a5b`, `#c9a227`, `#c0262d` | ✅ / ⚠️ / ❌ and OK / Watch / Concern |

The typeface is Inter (`next/font/google`). Charts use Recharts; motion uses Motion; icons are Phosphor.

## Copy

All user-facing text is English and lives in `lib/copy.ts` and `lib/content/*.ts`, read through
`useT`. The disclaimer and forbidden-phrase rules apply: a test checks every string against
`configs/forbidden_phrases.yaml`.

## Tests

```bash
cd frontend
pnpm lint && pnpm typecheck
pnpm test                 # Vitest unit and component tests (lib/*.test.ts, components/**/*.test.tsx)
pnpm test:e2e             # Playwright on the mocks (own server on :3100)
E2E_REAL=1 pnpm test:e2e  # against a running app (:3000) and API (:8000)
pnpm build
```

The `frontend` CI workflow runs lint, typecheck, unit tests and the build, and Playwright in a second
job ([Development](../development/index.md#ci)).
