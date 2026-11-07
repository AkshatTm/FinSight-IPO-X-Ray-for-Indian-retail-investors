> **Historical record (final session (v1.1)).** Kept as written; it may describe plans that changed or were cut. Current state: the [FinSight docs site](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/docs/index.md) and [FINAL_SCORECARD](https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors/blob/main/eval_results/final/FINAL_SCORECARD.md).

# API contract for the final frontend

Owner: Opus. Source of truth for types: `openapi.json` (regenerate with `uv run poe gen-openapi`).
All new fields are **additive and nullable**: old reports without them still validate.

## `GET /api/docs/{doc_id}/report` → `ReportOverview`

```jsonc
{
  "doc": { /* DocRecord: doc_id, company, doc_type, status, analysis_status, ... */ },
  "companion_doc_id": null,
  "facts_summary": { /* summary.json: revenue, profit_after_tax, peers, litigation, ... */ },
  "risk_level": { /* risklevel.json */ },
  "top_risks": [ /* up to 5 risks, ranked */ ],
  "redflags_summary": [ { "id": "RF01", "status": "ok" } ],
  "offer_line_params": null,
  "sod": { /* NEW: sod.json, see below; null when the sod stage has not run */ }
}
```

`sod` is `null` for uploads analysed before CC-06. After the Step 2 `pipeline_version` bump every
re-analysed or newly uploaded IPO has it.

## `sod` (= `SODResult`, `src/finsight/summary/sod.py`)

| Field | Type | Notes |
|---|---|---|
| `doc_id`, `pipeline_version` | str | |
| `has_sod` | bool | false = RHP has no "Summary of the Offer Document" (e.g. Jio); values come from fallbacks |
| `source` | `{financials, holdings, litigation, rpt, objects: str}` | `sod`, `window` or `fallback:<section>` |
| `currency_unit` | str | e.g. `"million"` (display hint only; amounts are already in ₹) |
| `financials` | `{row_key: SummaryValue[]}` | see rows below |
| `derived` | `Ratio[]` | computed ratios with formula + input pages |
| `promoter_holding_pre` | `SummaryValue \| null` | percent, pre-offer |
| `promoter_holding_post` | `SummaryValue \| null` | percent, post-offer (often null until the price is known) |
| `litigation` | `{key: SummaryValue}` | `criminal_cases`, ... (count) |
| `rpt_total` | `SummaryValue \| null` | related-party total |
| `auditor_remarks` | `SummaryValue[]` | |
| `strengths` | `{heading, sentence, page}[]` | the issuer's own "Our Strengths" list |
| `price_band` | `{low, high, source: "user"\|"announcement", ref} \| null` | never read from the RHP; null today |

### `financials` row keys
`revenue`, `profit_after_tax`, `operating_cash_flow` (3 fiscal years: `latest`, `latest-1`, `latest-2`),
`net_worth`, `total_borrowings` (`latest` + `stub`),
`equity_share_capital`, `total_income`, `eps_basic`, `eps_diluted`, `nav_per_share`
(3 FY + an optional stub period). **The stub's `period` is free text as printed**, e.g.
`"Three months periods ended June 30, 2026"`; treat any period that is not
`latest|latest-1|latest-2` as the stub.

### `SummaryValue`
```json
{
  "key": "revenue",
  "period": "latest",
  "status": "found",
  "value": {"kind": "money", "value_inr": "1468853000000", "currency": "INR",
            "raw": "1,468,853", "scale_word": "million", "precision": 0},
  "evidence": {"doc_id": "doc_72480c2e249eb8da", "page": 76, "bbox": [77.4, 169.5, 420.5, 179.4],
               "sentence": "Revenue from Operations — 2026: 1,468,853 (₹ in million)"}
}
```
- `status`: `found` | `stated_zero` | `not_found` (`value` is null when not found; show "not stated").
- `value.kind`: `money` (`value_inr` = full rupees as a decimal string), `percent` (`value`), `count` (`value`, `unit`).
- Per-share rows (`eps_*`, `nav_per_share`) are `money` with `value_inr` = ₹ per share.
- Format negatives as `−₹3.30` (minus before the rupee sign).

### `Ratio`
```json
{"key": "pat_margin", "period": "latest", "value": "20.46", "unit": "%",
 "formula": "profit after tax ÷ revenue from operations × 100",
 "inputs": ["profit after tax (latest): 300,527, p.76", "revenue (latest): 1,468,853, p.76"],
 "pages": [76], "status": "computed", "reason": null}
```
- `key`: `revenue_growth_yoy` (%), `pat_margin` (%), `debt_to_equity` (x), `operating_cash_flow` (₹, `as_printed`).
- `status`: `computed` | `as_printed` | `not_available` (then `value` is null and `reason` says why).
- `unit`: `%` | `x` | `₹`.

### Where the other ratios live
| Ratio | Path |
|---|---|
| EPS (basic / diluted) | `sod.financials.eps_basic` / `eps_diluted` |
| NAV per share | `sod.financials.nav_per_share`, else the issuer row of `facts_summary.peers` (`nav`) |
| RoNW, P/E | issuer row of `facts_summary.peers` (`is_issuer: true`; fields `ronw`, `pe`) from Basis for Offer Price. P/E is null in an RHP (price is `[●]`) |
| PAT margin, D/E | `sod.derived` |
| Promoter holding pre / post | `sod.promoter_holding_pre` / `promoter_holding_post` |
| Price band | `sod.price_band` (null today) |

## Real example (Jio Platforms, trimmed, from `doc_72480c2e249eb8da`)
```json
{
  "has_sod": false,
  "source": {"financials": "window", "holdings": "fallback:capital_structure",
             "litigation": "fallback:outstanding_litigation",
             "rpt": "fallback:summary_of_related_party_transactions",
             "objects": "fallback:objects_of_the_offer"},
  "currency_unit": "million",
  "financials": {
    "revenue": [{"period": "latest", "status": "found", "value": {"kind": "money", "value_inr": "1468853000000"}},
                {"period": "latest-1", "status": "found", "value": {"kind": "money", "value_inr": "1282184000000"}},
                {"period": "latest-2", "status": "found", "value": {"kind": "money", "value_inr": "1095581000000"}}],
    "profit_after_tax": [{"period": "latest", "value": {"value_inr": "300527000000"}}, "..."],
    "eps_basic": [{"period": "latest", "value": {"value_inr": "33.63"}},
                  {"period": "latest-1", "value": {"value_inr": "29.21"}},
                  {"period": "latest-2", "value": {"value_inr": "23.96"}},
                  {"period": "Three months periods ended June 30, 2026", "value": {"value_inr": "8.69"}}],
    "net_worth": [{"period": "latest", "value": {"value_inr": "3359769000000"}},
                  {"period": "stub", "status": "not_found", "value": null}]
  },
  "derived": [
    {"key": "revenue_growth_yoy", "period": "latest", "value": "14.56", "unit": "%", "status": "computed"},
    {"key": "pat_margin", "period": "latest", "value": "20.46", "unit": "%", "status": "computed"},
    {"key": "debt_to_equity", "period": "latest", "value": "0.21", "unit": "x", "status": "computed"}
  ],
  "promoter_holding_pre": {"key": "promoter_holding_pre_pct", "period": "pre-offer", "status": "found",
                           "value": {"kind": "percent", "value": "66.43", "raw": "66.43%"},
                           "evidence": {"page": 109}},
  "promoter_holding_post": null,
  "strengths": [{"heading": "A technology company with inherent engineering and full-stack proprietary capabilities",
                 "sentence": "Our platform is built on a vertically integrated proprietary technology stack ...",
                 "page": 206}],
  "price_band": null
}
```

## English only
From Step 3 the API is English-only. A stray `lang` query/body parameter is accepted and ignored
(no 422). Voice/ASR routes are removed; the frontend must not call them.

## Risk level (`risk_level` in the report)
- `percentile` is now **`null`** (C-ADR-28) and `percentile_note` carries the reason. Hide any
  "riskier than X% of past IPOs" line; keep `level` (low / medium / high) and the disclaimer.
- `forced_by` lists only severe findings **about the issuer** (C-ADR-26).

## Severe findings (`redflags.json` `severe_overrides[]`)
- New field `about`: `issuer` | `promoter` | `group_company` | `director`.
- Only `issuer` findings force High. Show the others as findings with a label such as
  "About the promoter, not the company"; they do not set the level.

## Compare (`GET /api/docs/{doc_id}/compare`)
- The issuer peer row printed as "The Company" / "Our Company" / "Issuer" is now returned with the
  company's name (applied when served, so old analyses are fixed too).
- **Frontend to do (Sonnet):** `frontend/lib/compare.ts` `peerCell` prints `₹-3.30` for a loss;
  print `−₹3.30` (U+2212 minus before the rupee sign). Same for any other money formatter.
