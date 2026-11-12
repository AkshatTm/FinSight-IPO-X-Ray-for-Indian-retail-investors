// SYNTHETIC summary-of-offer block for the mock report (shape: docs/final/CONTRACT.md). Company and
// figures are made up, like the rest of mocks/report.ts.

const money = (inr: number, raw: string) => ({ kind: "money", value_inr: String(inr), currency: "INR", raw, scale_word: "million", precision: 0 });
const found = (key: string, period: string, inr: number, page: number, sentence = "") => ({
  key,
  period,
  status: "found",
  value: money(inr, String(inr / 1_000_000)),
  evidence: { doc_id: "mock", page, bbox: null, sentence },
});
const missing = (key: string, period: string) => ({ key, period, status: "not_found", value: null, evidence: null });
const STUB = "Three months period ended June 30, 2026";
const M = 1_000_000;

export const MOCK_SOD = {
  doc_id: "mock",
  pipeline_version: "mock",
  has_sod: true,
  currency_unit: "million",
  financials: {
    revenue: [
      found("revenue", "latest-2", 9_820 * M, 76, "Revenue from Operations — 2024: 9,820 (₹ in million)"),
      found("revenue", "latest-1", 11_450 * M, 76),
      found("revenue", "latest", 13_980 * M, 76, "Revenue from Operations — 2026: 13,980 (₹ in million)"),
    ],
    total_income: [found("total_income", "latest-2", 9_990 * M, 76), found("total_income", "latest-1", 11_700 * M, 76), found("total_income", "latest", 14_310 * M, 76)],
    profit_after_tax: [found("profit_after_tax", "latest-2", 640 * M, 76), found("profit_after_tax", "latest-1", 905 * M, 76), found("profit_after_tax", "latest", 1_210 * M, 76)],
    operating_cash_flow: [found("operating_cash_flow", "latest-2", 410 * M, 80), found("operating_cash_flow", "latest-1", -120 * M, 80), found("operating_cash_flow", "latest", 760 * M, 80)],
    net_worth: [found("net_worth", "latest", 6_240 * M, 76), found("net_worth", "stub", 6_510 * M, 76)],
    total_borrowings: [found("total_borrowings", "latest", 1_940 * M, 76), missing("total_borrowings", "stub")],
    eps_basic: [
      found("eps_basic", "latest-2", 6.4 * 1, 76),
      found("eps_basic", "latest-1", 9.05, 76),
      found("eps_basic", "latest", 12.1, 76),
      { ...found("eps_basic", STUB, 3.3, 76), period: STUB },
    ],
    nav_per_share: [found("nav_per_share", "latest", 62.4, 76)],
  },
  derived: [
    { key: "revenue_growth_yoy", period: "latest", value: "22.10", unit: "%", formula: "(revenue this year − revenue last year) ÷ revenue last year × 100", inputs: [], pages: [76], status: "computed", reason: null },
    { key: "pat_margin", period: "latest", value: "8.66", unit: "%", formula: "profit after tax ÷ revenue from operations × 100", inputs: [], pages: [76], status: "computed", reason: null },
    { key: "debt_to_equity", period: "latest", value: "0.31", unit: "x", formula: "total borrowings ÷ net worth", inputs: [], pages: [76], status: "computed", reason: null },
    { key: "operating_cash_flow", period: "latest", value: null, unit: "₹", formula: null, inputs: [], pages: [], status: "not_available", reason: "Not printed in the summary." },
  ],
  promoter_holding_pre: { key: "promoter_holding_pre_pct", period: "pre-offer", status: "found", value: { kind: "percent", value: "66.43", raw: "66.43%" }, evidence: { page: 109 } },
  promoter_holding_post: null,
  strengths: [
    { heading: "A market leader in its niche chemicals", sentence: "We are among the largest producers of speciality intermediates in India by volume in Fiscal 2026.", page: 120 },
    { heading: "Long relationships with blue-chip customers", sentence: "Our top ten customers have bought from us for more than ten years on average.", page: 121 },
    { heading: "Integrated manufacturing", sentence: "Backward integration lowers our input costs and shortens delivery times.", page: 122 },
  ],
  price_band: null,
};

export const MOCK_FACTS = {
  peers: [{ name: "Acme Speciality Chemicals Limited", is_issuer: true, pe: null, ronw: "19.4", nav: "62.40", eps: "12.10", evidence: { page: 88 } }],
};
