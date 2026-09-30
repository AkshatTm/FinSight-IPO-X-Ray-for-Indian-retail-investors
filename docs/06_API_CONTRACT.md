# 06 — API Contract

FastAPI backend, base path **`/api`**. Every response body is a pydantic model; `uv run poe gen-openapi` writes `openapi.json`, and the frontend generates `lib/api/types.ts` from it. Changing a shape = changing this doc + the model + regenerating types, in one PR (`feat(api)!:` if breaking).

Conventions: JSON, `snake_case` keys, money values as **strings** of decimals (`"8000000000.00"`) to avoid float errors, pages 1-indexed, bboxes in PDF points `[x0, y0, x1, y1]` with page width/height provided so the client can scale.

---

## 1. Errors

All non-2xx responses:
```json
{"error": {"code": "ipo_not_found", "message": "No IPO with id 'xyz'.", "hint": "Check /api/ipos for valid ids.", "trace_id": null}}
```
Codes: `ipo_not_found`, `page_out_of_range`, `llm_unavailable`, `models_warming_up`, `asr_failed`, `audio_too_long`, `validation_error`, `internal_error`. Stack traces never appear in responses.

---

## 2. Endpoints

### `GET /api/health`
```json
{"status": "ok | warming | degraded", "profile": "full", "demo_mode": false,
 "models": {"llm": {"name": "qwen3.5:2b", "loaded": true}, "dense": {"loaded": true},
            "reranker": {"loaded": true}, "asr": {"loaded": false, "lazy": true}},
 "version": "0.6.0", "git_sha": "abc1234"}
```

### `GET /api/ipos`
Query: `q`, `sector`, `year`, `sort=listing_date|issue_size`.
```json
[{"id": "acme-industries-2025", "company": "Acme Industries Ltd", "sector": "Industrials",
  "listing_date": "2025-11-14", "rhp_pages": 612,
  "issue_size_inr": "12500000000.00", "fresh_inr": "8000000000.00", "ofs_inr": "4500000000.00",
  "xray_status": "ready"}]
```

### `GET /api/ipos/{id}`
Metadata + section list:
```json
{"id": "...", "company": "...", "rhp_pages": 612, "page_size": {"width": 612, "height": 792},
 "sections": [{"id": "the_offer", "title": "THE OFFER", "start_page": 67, "end_page": 68}]}
```

### `GET /api/ipos/{id}/xray`
```json
{"ipo_id": "...", "company": "...", "built_at": "...",
 "fields": [{
   "field_id": "fresh_issue_size", "label_en": "Fresh issue", "label_hi": "नया निर्गम (फ्रेश इश्यू)",
   "type": "money",
   "value": {"kind": "money", "value_inr": "8000000000.00", "raw": "₹ 800.00 crore", "scale_word": "crore", "precision": 2},
   "page": 12, "bbox": [72.0, 410.2, 301.5, 422.8],
   "extractor": "qa_finetuned", "score": 0.93,
   "verdict": "verified", "reason_code": "verified", "reason": "Matches The Offer (p. 67).",
   "checks": [{"check": "total_equals_fresh_plus_ofs", "status": "verified", "reason": "..."}],
   "candidates": [{"extractor": "rules", "raw": "...", "value": {...}, "page": 1, "score": 1.0, "gold_match": true}]
 }],
 "derived": {"fresh_share_pct": "64.00", "ofs_share_pct": "36.00"}}
```
`value.kind` ∈ `money | count | percent | range | placeholder | text | list | table`. `gold_match` present only for IPOs with gold labels.

### `GET /api/ipos/{id}/pages/{n}`
`image/webp`. `Cache-Control: public, max-age=31536000, immutable`.

### `GET /api/ipos/{id}/pages/{n}/words`
```json
{"page": 12, "width": 612, "height": 792, "words": [{"t": "Fresh", "b": [72.0, 410.2, 98.1, 422.8]}]}
```

### `GET /api/ipos/{id}/suggested-questions`
```json
[{"text": "What will the company do with the money raised?", "language": "en", "kind": "normal"},
 {"text": "Is the fresh issue ₹800 lakh?", "language": "en", "kind": "trick"},
 {"text": "इस IPO में प्रमोटर कौन हैं?", "language": "hi", "kind": "normal"},
 {"text": "Should I apply for this IPO?", "language": "en", "kind": "advice"}]
```

### `POST /api/chat` → `text/event-stream`
Request:
```json
{"ipo_id": "acme-industries-2025", "question": "What is the fresh issue size?", "language": "en",
 "source": "typed | voice | chip", "demo": false}
```
Events (in order; `event:` name + JSON `data:`):

| Event | Data | Notes |
|---|---|---|
| `stage` | `{"name": "guard|retrieving|generating|verifying|done", "status": "start|end", "ms": 12}` | Drives the stage line and Inspector timeline |
| `guard` | `{"blocked": true, "reason": "advice_intent", "facts": [<xray field summaries>]}` | If `blocked`, stream ends after `final` |
| `retrieval` | `{"passages": [{"n": 1, "id": "...", "page_start": 67, "page_end": 67, "section": "the_offer", "snippet": "...", "bm25_rank": 2, "dense_rank": 1, "fused_rank": 1, "rerank_score": 0.91}], "dropped": [...]}` | |
| `abstain` | `{"reason": "low_retrieval_score", "closest_passage": {...}}` | Stream ends after `final` |
| `token` | `{"text": "The fresh"}` | Many |
| `answer` | `{"text": "...", "citations": [{"n": 1, "char_start": 45, "char_end": 48}]}` | Full text once |
| `verdict` | `{"index": 0, "answer_char_span": [23, 38], "answer_value": {...}, "status": "contradicted", "reason_code": "scale_mismatch", "reason": "...", "evidence": {"passage_id": "...", "page": 12, "char_span": [120, 134], "bbox": [...], "value": {...}}}` | One per number; frontend staggers the reveal |
| `final` | `{"trace_id": "01J...", "score": 0.75, "n_numbers": 4, "timings_ms": {"guard": 3, "retrieve": 410, "generate": 5200, "verify": 40}}` | Always last |
| `error` | `{"code": "llm_unavailable", "message": "..."}` | Then stream closes |

### `POST /api/voice`
`multipart/form-data`: `audio` (webm/opus or wav, ≤ 20 s), `language` (default `hi`).
```json
{"transcript": "इस आईपीओ में प्रमोटर कौन हैं?", "language": "hi", "asr_model": "...", "ms": 3400}
```
The client then calls `/api/chat` with `source: "voice"`.

### `GET /api/traces/{trace_id}`
Full `Trace` (see `02_ARCHITECTURE.md` §6): stages, passages (incl. dropped), prompt, checks, timings.

### `POST /api/normalize` ◇
`{"text": "₹12,500 mn and 1,250 cr"}` →
```json
{"amounts": [{"raw": "₹12,500 mn", "kind": "money", "value_inr": "125000000000.00",
  "equivalents": {"crore": "12,500.00", "million": "125,000.00", "lakh": "12,50,000.00"}}]}
```
(Illustrative numbers; tests define the truth.)

### `POST /api/extract/playground` ◇
`{"passage": "...", "field_id": "fresh_issue_size"}` →
```json
{"results": [{"extractor": "rules", "answer": "...", "score": 1.0},
             {"extractor": "qa_finetuned", "answer": "...", "score": 0.93,
              "tokens": ["Fresh", "Issue", "..."], "start_scores": [0.01, ...], "end_scores": [...]}]}
```

### Lab endpoints (read `eval_results/`)
- `GET /api/lab/ladder` → `ladder_table.json`
- `GET /api/lab/fields` → per-field × extractor matrix + 5 examples per cell
- `GET /api/lab/verifier` → P/R/F1 by type + confusion matrix
- `GET /api/lab/weaklabels` → stats + audit precision
- `GET /api/lab/frontier` (P1) → comparison table

### `GET /api/glossary?lang=en|hi`
Static reviewed entries: `[{"term": "offer_for_sale", "title": "Offer for sale (OFS)", "body": "..."}]`.

---

## 3. Demo cache

When `DEMO_MODE=1` (or request `demo: true`), `/api/chat` looks up `(ipo_id, normalized question, language)` in `demo_cache`. On hit it replays the stored event list with original inter-event delays; on miss it runs live. Cache entries are recorded from real runs with `uv run poe record-demo` — never hand-written.

## 4. CORS, limits

- CORS: `http://localhost:3000` and the Vercel domain (from config).
- Simple in-memory rate limit on `/api/chat` and `/api/voice` in `deploy_cpu` profile (e.g. 10/min per IP).
- Request body limit 5 MB (voice).
