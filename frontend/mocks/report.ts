import { delay, http, HttpResponse } from "msw";
import type { Schemas } from "@/lib/api/client";

// Risk report parts on mocks (B3.2 Compare; B3.1 adds the others). SYNTHETIC numbers made up
// for the UI, not from any real document. Refresh from the fixture pack (B0.4,
// tests/fixtures/real/samples/report_*.json.gz) once it lands. A doc_id containing "nopeers"
// returns the empty states.

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

export const reportHandlers = [
  http.get("/api/docs/:docId/compare", async ({ params }) => {
    await delay(120);
    if (String(params.docId).includes("nopeers")) {
      return HttpResponse.json({ peers: [], percentiles: [], peer_median_pe: null, provisional: true });
    }
    return HttpResponse.json(COMPARE);
  }),
];
