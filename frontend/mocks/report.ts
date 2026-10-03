import { delay, http, HttpResponse } from "msw";
import type { Schemas } from "@/lib/api/client";

// Risk report parts on mocks (B3.1, B3.2). SYNTHETIC: company, numbers and risk text are made up
// for the UI and come from no real document. Refresh from the fixture pack (B0.4,
// tests/fixtures/real/samples/report_*.json.gz) once it lands. `SAMPLE_DOC_ID` is a finished
// report you can open at /reports/<id>; any uploaded mock document gets the same parts. A doc_id
// containing "nopeers" returns the Compare empty states.

export const COMPARE: Schemas["Compare"] = {
  peers: [
    { name: "Acme Widgets Limited", pe: "20.66", eps: "12.10", ronw: "15.6", nav: "80.25", is_issuer: true, evidence: { doc_id: "mock", page: 88, bbox: null, sentence: null } },
    { name: "Beta Industries Limited", pe: "45.6", eps: "8.20", ronw: "18.2", nav: "55.00", is_issuer: false, evidence: { doc_id: "mock", page: 88, bbox: null, sentence: null } },
    { name: "Gamma Tools Limited", pe: null, eps: "-2.30", ronw: "-4.1", nav: "40.10", is_issuer: false, evidence: { doc_id: "mock", page: 88, bbox: null, sentence: null } },
    { name: "Delta Parts Limited", pe: "30.4", eps: "6.05", ronw: "12.0", nav: "61.00", is_issuer: false, evidence: { doc_id: "mock", page: 89, bbox: null, sentence: null } },
  ],
  peer_median_pe: "38.0",
  percentiles: [
    { metric: "issue_size_inr", value: 12_500_000_000, percentile: 71.5, corpus_n: 0 },
    { metric: "ofs_share", value: 0.65, percentile: 61.0, corpus_n: 0 },
    { metric: "insider_price_gap", value: 7.3, percentile: 73.4, corpus_n: 0 },
    { metric: "pe", value: 20.66, percentile: 30.2, corpus_n: 0 },
  ],
  provisional: true,
};

type Risk = Schemas["Risk"];
type Flag = Schemas["RedFlag"];

export const SAMPLE_DOC_ID = "doc_5a3f1e2b9c7d4a60";
const COMPANY = "Acme Speciality Chemicals Limited";

const SAMPLE_DOC: Schemas["DocRecord"] = {
  doc_id: SAMPLE_DOC_ID,
  sha256: "5a3f1e2b9c7d4a60".padEnd(64, "0"),
  doc_type: "rhp",
  company: COMPANY,
  pages: 412,
  uploaded_by: null,
  is_showcase: true,
  companion_of: null,
  created_at: "2026-10-02T09:30:00Z",
  status: "ready",
  rejection: null,
};

const ev = (page: number): Schemas["PageEvidence"] => ({ doc_id: SAMPLE_DOC_ID, page, bbox: null, sentence: null });
const flag = (id: string, title: string, status: Flag["status"], sentence: string, numbers: Record<string, string> = {}, page = 0, rule = ""): Flag => ({
  id, title, status, sentence, numbers_used: numbers, evidence: page ? [ev(page)] : [], rule, points: status === "concern" ? 2 : status === "watch" ? 1 : 0,
});

export const REDFLAGS: Schemas["RedFlags"] = {
  flags: [
    flag("RF01", "Profit or loss", "ok", "Profitable in each of the last 3 years (latest profit ₹212.4 crore).", { "Profit FY2026": "₹212.4 crore" }, 301, "Watch if the latest year is a loss; Concern if all of the last 3 years are losses."),
    flag("RF02", "Cash from the business", "watch", "The business used more cash than it brought in last year (₹-38.2 crore).", { "Operating cash flow FY2026": "₹-38.2 crore" }, 318, "Watch if negative in the latest year; Concern if negative in 2 of the last 3 years."),
    flag("RF03", "Debt", "ok", "Debt is 0.4× its net worth.", { "Debt": "₹410.0 crore", "Net worth": "₹1,025.0 crore" }, 305, "Watch above 1.0×; Concern above 2.0×."),
    flag("RF04", "Who gets the IPO money", "concern", "85.0% of the money goes to existing shareholders who are selling, not to the company.", { "Fresh issue": "₹150.0 crore", "Offer for sale": "₹850.0 crore" }, 12, "Watch above 50%; Concern above 80%."),
    flag("RF05", "What insiders paid", "watch", "Selling shareholders bought their shares at an average of ₹42.10. The IPO price is ₹310, about 7.4× more.", { "Average cost": "₹42.10", "Price": "₹310" }, 21, "Watch at 5× or more; Concern at 20× or more."),
    flag("RF06", "Founders' stake after the IPO", "ok", "Promoters will still own 61.2% of the company.", { "Promoter stake after": "61.2%" }, 88),
    flag("RF07", "Vague use of money", "not_applicable", "", {}, 0),
    flag("RF08", "Court cases", "watch", "There are 2 criminal case(s) involving the company, promoters or directors.", { "Criminal cases": "2" }, 377),
    flag("RF09", "Dealings with related companies", "ok", "Business with related parties was ₹31.0 crore, about 2.1% of revenue.", { "Related-party sales": "₹31.0 crore" }, 340),
    flag("RF10", "Dependence on a few customers", "watch", "The top customer brings in 18.0% of revenue, and the top 10 bring in 61.0%.", { "Top customer": "18.0%", "Top 10": "61.0%" }, 160),
    flag("RF11", "Price compared with listed peers", "ok", "At the IPO price, the P/E is 20.7. The listed peers named in the document have a median P/E of 38.0.", { "P/E": "20.7", "Peer median P/E": "38.0" }, 88),
    flag("RF12", "Auditor's remarks", "ok", "No remarks from the auditor in the summary."),
    flag("RF13", "Pledged promoter shares", "not_available", ""),
  ],
  financial_company: false,
  thresholds_version: "b01-v1",
};

const CATS: Risk["category"][] = ["financial", "customers_suppliers", "regulatory", "operations", "legal_litigation", "competition", "debt_liquidity", "promoters_governance", "technology_data", "market_macro"];
const SAMPLE_RISKS: Risk[] = Array.from({ length: 18 }, (_, i) => {
  const category = CATS[i % CATS.length];
  const novelty = [0.04, 0.72, 0.35, 0.08, 0.55, 0.9, 0.22, 0.61, 0.15, 0.4][i % 10];
  const ready = i < 12 && i !== 5;
  return {
    rid: `r${i + 1}`,
    order: i,
    title: `Synthetic risk ${i + 1}: our ${category?.replace("_", " ")} could be affected by changes we cannot control.`,
    body: `This is made-up text for the mock report (not from any document). Any adverse development may affect our business, results of operations and financial condition. In FY2025 we recorded ₹${(i + 1) * 3}.5 crore of related losses.`,
    page_start: 30 + i * 2,
    page_end: 31 + i * 2,
    group: i < 14 ? "Internal risks" : "External risks",
    category,
    category_conf: 0.8,
    novelty,
    nearest_examples: [{ company: "Example Past IPO Limited", year: 2021, title: "A similar synthetic risk", similarity: 0.83 }],
    hedging: { hedge_count: i % 4, hard_fact: i % 3 === 0, flag: i % 6 === 0, fact_sentence: null },
    numbers: [{ kind: "money", value_inr: String((i + 1) * 35_000_000), currency: "INR", raw: `₹${(i + 1) * 3}.5 crore`, scale_word: "crore", precision: 1 }],
    seriousness: i % 3 === 0 ? "high" : i % 3 === 1 ? "medium" : "low",
    importance: Math.round((1 - i / 20) * 100) / 100,
    simple: ready ? `Plain English (synthetic): the company says ${category?.replace("_", " ")} problems could hurt it, and it already lost ₹${(i + 1) * 3}.5 crore this way in FY2025.` : null,
    simple_status: i === 5 ? "rejected" : ready ? "ready" : "pending",
    simple_checks: [],
  };
});

const queue = new Set<string>(["r13", "r14", "r15"]);

export const RISK_LEVEL: Schemas["RiskLevel"] = {
  level: "medium",
  points: 9,
  max_points: 26,
  score: 0.3462,
  percentile: 62.4,
  checks_available: 11,
  reasons: [
    { source: "redflag", id: "RF04", label: "Who gets the IPO money", points: 2, link: "#redflag-RF04" },
    { source: "redflag", id: "RF02", label: "Cash from the business", points: 1, link: "#redflag-RF02" },
    { source: "redflag", id: "RF05", label: "What insiders paid", points: 1, link: "#redflag-RF05" },
    { source: "redflag", id: "RF08", label: "Court cases", points: 1, link: "#redflag-RF08" },
    { source: "redflag", id: "RF10", label: "Dependence on a few customers", points: 1, link: "#redflag-RF10" },
    { source: "risk", id: "r1", label: "Synthetic risk 1", points: 1, link: "#risk-r1" },
    { source: "risk", id: "r4", label: "Synthetic risk 4", points: 1, link: "#risk-r4" },
  ],
  thresholds: { low_below: 0.2, high_from: 0.4 },
  corpus_n: 0,
  provisional: true,
  behind_click: false,
  disclaimer_key: "risklevel.disclaimer",
};

function overview(doc: Schemas["DocRecord"]): Schemas["ReportOverview"] {
  return {
    doc,
    companion_doc_id: null,
    facts_summary: null,
    risk_level: RISK_LEVEL as unknown as Record<string, unknown>,
    top_risks: SAMPLE_RISKS.slice(0, 5) as unknown as Record<string, unknown>[],
    redflags_summary: REDFLAGS.flags!.map((f) => ({ id: f.id, status: f.status })),
    offer_line_params: doc.doc_type === "drhp" ? { doc_type: "drhp" } : { company: doc.company ?? COMPANY, fresh_crore: "150", ofs_crore: "850", price: "310", doc_type: doc.doc_type },
  };
}

function risksPage(url: URL): Schemas["RisksPage"] {
  const sort = url.searchParams.get("sort") ?? "importance";
  const category = url.searchParams.get("category");
  const q = (url.searchParams.get("q") ?? "").toLowerCase();
  const unusual = url.searchParams.get("unusual_only") === "true";
  const counts = new Map<string, number>();
  for (const r of SAMPLE_RISKS) counts.set(String(r.category), (counts.get(String(r.category)) ?? 0) + 1);
  let risks = SAMPLE_RISKS.filter((r) => (!category || r.category === category) && (!unusual || (r.novelty ?? 1) < 0.1));
  if (q) risks = risks.filter((r) => `${r.title}\n${r.body}\n${r.simple ?? ""}`.toLowerCase().includes(q));
  risks = [...risks].sort((a, b) =>
    sort === "order" ? a.order - b.order : sort === "category" ? String(a.category).localeCompare(String(b.category)) || a.order - b.order : (b.importance ?? 0) - (a.importance ?? 0),
  );
  return {
    n_total: SAMPLE_RISKS.length,
    groups: [...counts].map(([category, count]) => ({ category: category as NonNullable<Risk["category"]>, count })).sort((a, b) => b.count - a.count),
    risks,
    queued: [...queue],
  };
}

export const reportHandlers = [
  http.get(`/api/docs/${SAMPLE_DOC_ID}`, () => HttpResponse.json({ doc: SAMPLE_DOC, job_id: null, stages: [], companion_doc_id: null })),
  http.get("/api/docs/:docId/report", async ({ params }) => {
    await delay(100);
    const id = String(params.docId);
    return HttpResponse.json(overview(id === SAMPLE_DOC_ID ? SAMPLE_DOC : { ...SAMPLE_DOC, doc_id: id, company: COMPANY }));
  }),
  http.get("/api/docs/:docId/risk-level", () => HttpResponse.json(RISK_LEVEL)),
  http.get("/api/docs/:docId/redflags", async () => {
    await delay(100);
    return HttpResponse.json(REDFLAGS);
  }),
  http.get("/api/docs/:docId/risks", async ({ request }) => {
    await delay(100);
    return HttpResponse.json(risksPage(new URL(request.url)));
  }),
  http.post("/api/docs/:docId/risks/:rid/simplify", ({ params }) => {
    const rid = String(params.rid);
    const risk = SAMPLE_RISKS.find((r) => r.rid === rid);
    if (!risk) return HttpResponse.json({ error: { code: "risk_not_found", message: "We couldn't find this risk in the report." } }, { status: 404 });
    if (risk.simple_status === "ready") return HttpResponse.json({ rid, simple_status: "ready", position: -1 });
    queue.add(rid);
    setTimeout(() => {
      queue.delete(rid);
      Object.assign(risk, { simple_status: "ready", simple: `Plain English (synthetic): ${risk.title.replace(/^Synthetic risk \d+: /, "")}` });
    }, 1500);
    return HttpResponse.json({ rid, simple_status: "pending", position: 0 });
  }),
  http.get("/api/docs/:docId/compare", async ({ params }) => {
    await delay(120);
    if (String(params.docId).includes("nopeers")) {
      return HttpResponse.json({ peers: [], percentiles: [], peer_median_pe: null, provisional: true });
    }
    return HttpResponse.json(COMPARE);
  }),
];
