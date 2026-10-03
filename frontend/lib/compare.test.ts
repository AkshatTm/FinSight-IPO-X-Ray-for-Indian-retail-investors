import { describe, expect, it } from "vitest";
import { metricValue, orderPeers, peerCell, roundPercentile, sourcePage, type Peer } from "./compare";

const peer = (name: string, extra: Partial<Peer> = {}): Peer =>
  ({ name, pe: null, eps: null, ronw: null, nav: null, is_issuer: false, evidence: null, ...extra }) as Peer;

describe("compare helpers", () => {
  it("puts the issuer first and keeps document order", () => {
    const out = orderPeers([peer("B"), peer("A", { is_issuer: true }), peer("C")]);
    expect(out.map((p) => p.name)).toEqual(["A", "B", "C"]);
  });
  it("formats cells and blanks", () => {
    expect(peerCell("45.6", "pe")).toBe("45.6");
    expect(peerCell("12.1", "eps")).toBe("₹12.10");
    expect(peerCell("18.2", "ronw")).toBe("18.2%");
    expect(peerCell(null, "nav")).toBe("—");
  });
  it("formats metrics", () => {
    expect(metricValue("issue_size_inr", 12_500_000_000)).toBe("₹1,250.00 crore");
    expect(metricValue("ofs_share", 0.65)).toBe("65.0%");
    expect(metricValue("insider_price_gap", 7.25)).toBe("7.3×");
    expect(metricValue("pe", 20.66)).toBe("20.7");
  });
  it("rounds percentiles into 0-99", () => {
    expect(roundPercentile(100)).toBe(99);
    expect(roundPercentile(-0.2)).toBe(0);
    expect(roundPercentile(64.5)).toBe(65);
  });
  it("finds the source page", () => {
    expect(sourcePage([peer("A"), peer("B", { evidence: { doc_id: "d", page: 88, bbox: null, sentence: null } })])).toBe(88);
    expect(sourcePage([])).toBeNull();
  });
});
