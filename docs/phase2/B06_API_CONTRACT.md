# B06 — API Contract additions (Big Phase 2)

Base path `/api`. Conventions from `06_API_CONTRACT.md` apply (snake_case, money as decimal strings, 1-indexed pages, error envelope). Every new response is a pydantic model; `openapi.json` is regenerated and the frontend types regenerated in the same PR.

## 1. Auth
- Frontend signs in with Supabase Auth (Google provider) and sends `Authorization: Bearer <supabase_jwt>`.
- The API verifies the JWT (Supabase JWKS), creates/updates `users` on first call.
- Required for: `POST /uploads`, `GET /me/*`, `POST …/simplify` (prioritise). Everything else is public for showcase and shared reports.
- New error codes: `unauthorized` (401), `quota_exceeded` (429, body has `limit`, `resets_at`), `global_quota_exceeded` (429).

## 2. Uploads and jobs

### `POST /api/uploads/init`
Body: `{filename, size_bytes, sha256}` →
- If `sha256` already processed: `{status: "exists", doc_id}`.
- Else: `{status: "upload", doc_id, upload_url, expires_at}` (signed GCS PUT URL in cloud; local profile returns `/api/uploads/{doc_id}/file`).
Checks: auth, quota, size ≤ 60 MB.

### `PUT {upload_url}` (direct to storage) or `POST /api/uploads/{doc_id}/file` (local)
Raw PDF bytes.

### `POST /api/uploads/{doc_id}/complete`
→ `{doc_id, job_id, status: "queued"}`. Starts validation + the job. Rejections return 422 with `code` ∈ `scanned | password | too_large | too_many_pages | not_offer_document`.

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
Reconnects with `Last-Event-ID` replay from `job_events`.

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
Moves the risk to the front of the simplification queue. → `{rid, simple_status, position}`.

### `GET /api/docs/{doc_id}/risk-level`
`RiskLevel`.

### `GET /api/docs/{doc_id}/compare`
`{peers: [{name, pe, eps, ronw, nav, is_issuer, evidence}], percentiles: [{metric, value, percentile, corpus_n}]}`.

### Existing endpoints, re-keyed
`/api/ipos/{id}/…` keeps working for showcase IPOs and is aliased to `/api/docs/{doc_id}/…` (`xray`, `pages/{n}`, `pages/{n}/words`, `suggested-questions`). Chat: `POST /api/chat` accepts `doc_id` (or `ipo_id` for backward compatibility).

## 4. Library
`GET /api/ipos` gains `recent_public: [{doc_id, company, doc_type, risk_level, created_at}]` (last 10 completed uploads, public only).

## 5. Lab
`GET /api/lab/b/{segmentation|summary|redflags|classifier|seriousness|simplify|readability|novelty|risklevel|latency|cost}` → files in `eval_results/b/`.

## 6. Admin (Akshat only, by email allow-list)
`GET /api/admin/costs` → per-day uploads, GPU seconds, estimated cost; `GET /api/admin/jobs?status=failed`.

## 7. Health
`/api/health` adds `{queue_length, vllm: {reachable, model}, worker_last_job_s, storage, db}`.
