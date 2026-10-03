# B06 — API Contract additions (Big Phase 2)

Base path `/api`. Conventions from `06_API_CONTRACT.md` apply (snake_case, money as decimal strings, 1-indexed pages, error envelope). Every new response is a pydantic model; `openapi.json` is regenerated and the frontend types regenerated in the same PR.

## 1. Auth
- Frontend signs in with Supabase Auth (Google provider) and sends `Authorization: Bearer <supabase_jwt>`.
- The API verifies the JWT (Supabase JWKS with an HS256 fallback; checks `aud = authenticated` and `iss`), creates/updates `users` on first call.
- Required for: `POST /uploads/*`, `GET /me/*`. `POST …/simplify` is **auth optional and rate-limited per IP**. Everything else is public for showcase and shared reports.
- New error codes: `unauthorized` (401), `quota_exceeded` (429, body has `limit`, `resets_at`), `global_quota_exceeded` (429), `uploads_disabled` (503, kill switch), `hash_mismatch` (422).

## 2. Uploads and jobs

### `POST /api/uploads/init`
Body: `{filename, size_bytes, sha256}` →
- If `sha256` already processed: `{status: "exists", doc_id}`.
- Else: `{status: "upload", doc_id, upload_url, upload_method, expires_at}` (`PUT` to a V4 signed GCS URL in the cloud profiles; `POST /api/uploads/{doc_id}/file` in the local profiles).
Checks: auth, `UPLOADS_ENABLED` (503 `uploads_disabled`), quota (429 `quota_exceeded` / `global_quota_exceeded` with `limit` and `resets_at` = next midnight IST), size ≤ `uploads.max_mb` (422 `too_large`). A dedupe hit does not use quota. The doc row starts with `status: "uploading"` and is hidden from every read endpoint until `complete`.

### `PUT {upload_url}` (direct to storage) or `POST /api/uploads/{doc_id}/file` (local)
Raw PDF bytes.

### `POST /api/uploads/{doc_id}/complete`
→ `{doc_id, job_id, status: "queued"}`. **Recomputes SHA-256 on the server** (mismatch → 422 `hash_mismatch`, file deleted) and re-checks the size (422 `too_large`), then queues the job. `409 upload_not_started` if `init` was not called or the file has not arrived. The PDF is validated by the worker, never in the API process (B02 §11): `scanned | password | too_many_pages | not_offer_document` arrive as the `validated` stage failure (`detail.reason`) and as `doc.rejection`, with `doc.status = "failed"`.

### `GET /api/docs/{doc_id}`
`DocRecord` + `{stages: [{stage, status, started_at, finished_at, detail}], companion_doc_id?}`.

### `GET /api/docs/{doc_id}/events` → `text/event-stream`
Events in order (each `data:` is JSON):
| Event | Data |
|---|---|
| `stage` | `{stage, status: "start"|"end"|"failed", detail?}` |
| `progress` | `{stage, done, total}` (parse pages, simplify items) |
| `ready` | `{part: "facts"|"redflags"|"risk_level"|"risks"|"compare"|"chat"}` — the UI fetches that part |
| `risk_simplified` | `{rid, simple_status}` |
| `done` | `{status: "ready"|"partial"|"failed", failed_stages: []}` |
Reconnects with `Last-Event-ID` replay from `job_events` (the API polls the table about once a second; the Supabase pooler has no LISTEN/NOTIFY).

**Stage → event map (B02 §3.1 and B05 §4 follow this):** every B02 stage id emits `stage` start/end/failed; `parsed` and `simplify` also emit `progress`; `ready` parts: `facts` after `facts`, `redflags` after `redflags`, `risks` after `risks_scored`, `risk_level` after `risk_level`, `compare` after `compare`, `chat` after `index`. B02's per-stage payloads go in `detail`.

### `GET /api/me/uploads`
`[{doc_id, company, doc_type, created_at, status}]`.

## 3. Report parts (all public)

### `GET /api/docs/{doc_id}/report`
Assembled overview: `{doc, facts_summary, risk_level, top_risks: [Risk (5)], redflags_summary: [{id, status}], offer_line_params}`. ETag + `Cache-Control: public, max-age=3600` for `status=ready`.

### `GET /api/docs/{doc_id}/redflags`
`{flags: [RedFlag], financial_company: bool, thresholds_version}`.

### `GET /api/docs/{doc_id}/risks?sort=importance|order|category&category=&q=&unusual_only=`
`{n_total, groups: [...], risks: [Risk]}`. `body` truncated to 1,200 chars; full body via the single endpoint.

### `GET /api/docs/{doc_id}/risks/{rid}`
Full `Risk` + `nearest_examples`.

### `POST /api/docs/{doc_id}/risks/{rid}/simplify` (auth optional; rate-limited)
Adds the risk to the simplification queue (or moves it to the front). Only the top 15 risks are queued automatically; any other risk is queued by this call. → `{rid, simple_status, position}`.

### `GET /api/docs/{doc_id}/risk-level`
`RiskLevel` (with `score`, `max_points`, `checks_available`, `corpus_n` and `behind_click: bool` from config).

### `GET /api/docs/{doc_id}/compare`
`{peers: [{name, pe, eps, ronw, nav, is_issuer, evidence}], percentiles: [{metric, value, percentile, corpus_n}]}`.

### Existing endpoints, re-keyed
`/api/ipos/{id}/…` keeps working for showcase IPOs and is aliased to `/api/docs/{doc_id}/…` (`xray`, `pages/{n}`, `pages/{n}/words`, `suggested-questions`). Chat: `POST /api/chat` accepts `doc_id` (or `ipo_id` for backward compatibility).

## 4. Library
`GET /api/ipos` gains `recent_public: [{doc_id, company, doc_type, risk_level, created_at}]` (last 10 completed uploads, public only).

## 5. Lab
`GET /api/lab/b/{name}` → files in `eval_results/b/`:

| name | file(s) |
|---|---|
| segmentation | `segmentation.json` |
| summary | `summary_extraction.json` |
| redflags | `redflags.json` |
| classifier | `classifier_*.json` (merged list) |
| seriousness | `seriousness.json` |
| simplify | `simplify_human.json` + `simplify_checks.json` |
| readability | `readability.json` |
| novelty | `novelty.json` |
| risklevel | `risklevel_validation.json` |
| latency | `latency_cloud.json` |
| cost | `cost.json` |

A missing file → 404 `not_available` (Phase 1 rule); the Lab hides that section.

## 6. Admin (Akshat only, by email allow-list)
`GET /api/admin/costs` → per-day uploads, CPU (and GPU) seconds, share of the free grant, estimated cost; `GET /api/admin/jobs?status=failed`.

## 7. Health
`/api/health` adds `{queue_length, uploads_enabled, llm: {backend, model, loaded}, worker_last_job_s, storage, db}` (`vllm` only on the optional GPU path).
