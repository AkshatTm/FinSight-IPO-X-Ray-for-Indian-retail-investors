# Security review (B3.5a)

A review of the Phase 2 API, storage, jobs and auth code against the checklist in B02 §11, done in
the B3.5a cloud session (overnight run 1) on code only. Nothing was deployed. Items that need the
real stack are listed under "Verify on the deployed stack" and run in B3.5b.

Status: ✅ holds and is tested · 🔧 fixed in this part · ⚠️ open, with the follow-up named.

## Findings

| # | Area | Finding | Status |
| --- | --- | --- | --- |
| 1 | Uploads (local profile) | `POST /api/uploads/{doc_id}/file` checked `Content-Length` but then read the whole body before checking its size. A chunked body has no length, so it could fill memory. | 🔧 The body is read in chunks and cut off at `uploads.max_mb` (test: `test_chunked_body_without_length_is_cut_off_at_the_limit`). |
| 2 | Uploads (cloud) | `POST /api/uploads/{doc_id}/complete` downloaded the stored object before checking its size. A V4 signed PUT does not cap the size, so a huge object would be loaded into the API's memory. | 🔧 `Storage.size()` reads the size from metadata (`stat` locally, `get_blob().size` on GCS); oversized files are deleted unread (test: `test_oversized_stored_file_is_refused_before_it_is_read`). |
| 3 | Rate limit on `…/simplify` | The per-IP window used the socket peer. Behind the Vercel rewrite and Cloud Run that is a proxy address, so every reader shares one bucket; trusting `X-Forwarded-For` blindly would let anyone pick their own key. | 🔧 `uploads.trusted_proxy_hops` (default 0) takes the entry the trusted proxies added, counted from the right, and ignores the rest (tests: `test_client_ip_trusts_only_the_configured_proxy_hops`). ⚠️ Set the value after checking the header on the deployed stack (B3.5b). The cost stays bounded either way: simplify only re-orders an existing queue. |
| 4 | Admin data | Costs and failed jobs had no screen and no access rule. | 🔧 `/api/admin/costs` and `/api/admin/jobs` need a user whose email is in `auth.admin_emails` (401 without a token, 403 for others); the job list shows the rejection code, the failed stage names or a short launch message, never a stack trace. |
| 5 | Auth | Supabase JWTs are checked with JWKS (asymmetric) or the HS256 secret, with `aud` and `iss`. | ✅ `tests/auth`, `tests/api/test_admin.py` |
| 6 | Dedupe poisoning | The server recomputes the SHA-256 and deletes the object on a mismatch. | ✅ `test_hash_mismatch_is_rejected_and_file_removed` |
| 7 | Storage keys | Keys with `..`, a leading `/` or `\` are refused; `doc_id` path parameters are pattern-checked and cannot contain `/`. | ✅ `tests/storage` |
| 8 | Signed URLs | Upload links are V4 signed and expire after `storage.signed_url_ttl_s` (900 s). | ✅ `test_gcs_signed_upload_is_a_v4_put` |
| 9 | Error detail | Stage errors stay in the job row; events and API errors carry codes only. | ✅ `tests/jobs/test_failure_paths.py`, `test_worker_launch_failure_is_a_503_and_a_failed_job` |
| 10 | CORS | The API adds no CORS headers, so browsers only reach it through the same-origin Next.js rewrite; GCS has its own bucket CORS for the upload PUT. This is stricter than B02 §11 asks. | ✅ by design. If a direct cross-origin call is ever needed, allow only the Vercel domains. |
| 11 | PDF processing | PDFs are opened only in the worker job; the API never parses them. Page and size limits are checked in the `validated` stage. | ✅ `tests/jobs`, `tests/ingest` |
| 12 | Parse timeout | B02 §11 asks for a 10-minute parse timeout. Only the whole worker job has a limit (`deploy/gcp/worker-job.yaml`, 3,600 s); there is no per-stage limit. | ⚠️ A timeout per stage is a follow-up for B1.3a, when parsing joins the pipeline. |
| 13 | Privacy in risk text | Redacting personal addresses and contacts from risk bodies (B02 §11) needs the risk extraction stage, which is not built yet (B2.1a waits for the fixture pack). Rewrites already go through the forbidden-phrase and number checks. | ⚠️ Wire `retrieve.redact` into B2.1a. |
| 14 | Report access | A report can be read by anyone with its link (no owner check). | ✅ by design and stated in the privacy notice. |
| 15 | Secrets | No secret is in the frontend or the repository; `.env.example` holds names only; `scripts/check_env.py` never prints values. | ✅ |

## Verify on the deployed stack (B3.5b)

- Print `X-Forwarded-For` as the API sees it behind the Vercel rewrite and Cloud Run, then set
  `uploads.trusted_proxy_hops` (likely 2).
- Try an upload over 50 MB through the signed URL and check that `complete` refuses it without
  the API's memory jumping.
- Check that a token from another Supabase project gets 401 and a non-admin account gets 403 on
  `/admin/costs`.
- Check the GCS bucket CORS allows only the Vercel domains.
