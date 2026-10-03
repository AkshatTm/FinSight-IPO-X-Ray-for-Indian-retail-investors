import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CompareData } from "@/lib/compare";
import { CompareView } from "./CompareTab";

const DATA = {
  peers: [
    { name: "Beta Industries Ltd", pe: "45.6", eps: "8.2", ronw: "18.2", nav: "55", is_issuer: false, evidence: { doc_id: "d", page: 88, bbox: null, sentence: null } },
    { name: "Acme Widgets Limited", pe: "20.66", eps: "12.1", ronw: "15.6", nav: "80.25", is_issuer: true, evidence: null },
  ],
  peer_median_pe: "45.6",
  percentiles: [
    { metric: "ofs_share", value: 0.65, percentile: 64.6, corpus_n: 0 },
    { metric: "pe", value: 20.66, percentile: 20.7, corpus_n: 0 },
  ],
  provisional: true,
} as CompareData;

describe("CompareView", () => {
  it("shows the issuer first with the B05 columns, source chip and percentile lines", () => {
    render(<CompareView data={DATA} />);
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("Acme Widgets Limited")).toBeInTheDocument();
    expect(within(rows[1]).getByText("This IPO")).toBeInTheDocument();
    expect(screen.getByText("Return on net worth")).toBeInTheDocument();
    expect(screen.getByText("Basis for Offer Price, page 88")).toBeInTheDocument();
    expect(screen.getByText("Higher than 65% of past IPOs")).toBeInTheDocument();
    expect(screen.getByText("65.0%")).toBeInTheDocument();
    expect(screen.getByText(/Provisional/)).toBeInTheDocument();
    expect(screen.queryByText(/past Indian IPOs\.$/)).not.toBeInTheDocument(); // corpus_n 0: no count line
  });
  it("shows the B05 empty states", () => {
    render(<CompareView data={{ peers: [], percentiles: [], provisional: false } as CompareData} />);
    expect(screen.getByText("The document doesn't name listed peers.")).toBeInTheDocument();
    expect(screen.getByText("Not enough data to compare.")).toBeInTheDocument();
  });
});
