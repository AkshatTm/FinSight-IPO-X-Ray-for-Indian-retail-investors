import { describe, expect, it } from "vitest";
import { flagMatches, flagSentence, flagTitleKey, offerLine, plainState, sortFlags, tabForHash, topReasons, unusualness, type RedFlag, type RiskLevel } from "./report";

const f = (id: string, status: RedFlag["status"], sentence = "x") => ({ id, status, sentence }) as RedFlag;

describe("report helpers", () => {
  it("orders flags Concern, Watch, OK, NA and by id inside each", () => {
    const out = sortFlags([f("RF03", "ok"), f("RF09", "concern"), f("RF01", "not_available"), f("RF02", "watch"), f("RF04", "concern"), f("RF07", "not_applicable")]);
    expect(out.map((x) => x.id)).toEqual(["RF04", "RF09", "RF02", "RF03", "RF01", "RF07"]);
  });
  it("filters with NA covering not available and not applicable", () => {
    expect(flagMatches(f("RF07", "not_applicable"), "na")).toBe(true);
    expect(flagMatches(f("RF13", "not_available"), "na")).toBe(true);
    expect(flagMatches(f("RF04", "concern"), "watch")).toBe(false);
    expect(flagMatches(f("RF04", "concern"), "all")).toBe(true);
  });
  it("uses the B-FR-02 default line when a status has no sentence", () => {
    expect(flagSentence(f("RF13", "not_available", " "))).toBe("rf.missing");
    expect(flagSentence(f("RF01", "ok", "Profitable."))).toBe("Profitable.");
    expect(flagTitleKey("RF04")).toBe("rf.t.RF04");
    expect(flagTitleKey("RF14")).toBeNull();
  });
  it("labels unusualness at the B05 cut-offs", () => {
    expect(unusualness(0.04)).toEqual({ key: "rk.unusual", x: 4 });
    expect(unusualness(0.85)).toEqual({ key: "rk.common", x: 85 });
    expect(unusualness(0.6)).toEqual({ key: "rk.inPast", x: 60 });
    expect(unusualness(null)).toBeNull();
  });
  it("picks the plain-English state", () => {
    expect(plainState({ simple: "s", simple_status: "ready" }, false)).toBe("ready");
    expect(plainState({ simple: null, simple_status: "rejected" }, false)).toBe("rejected");
    expect(plainState({ simple: null, simple_status: "pending" }, true)).toBe("explaining");
    expect(plainState({ simple: null, simple_status: "pending" }, false)).toBe("not_queued");
    expect(plainState({ simple: null, simple_status: "failed" }, false)).toBe("not_queued");
  });
  it("builds the offer line variants", () => {
    expect(offerLine({ company: "Acme", fresh_crore: "150", ofs_crore: "850", price: "310" })).toEqual({
      key: "ov.offer",
      vars: { company: "Acme", fresh: "150", ofs: "850", price: "310" },
    });
    expect(offerLine({ ofs_crore: "500", fresh_crore: "0" })?.key).toBe("ov.offerOfs");
    expect(offerLine({ doc_type: "drhp" })?.key).toBe("ov.offerDrhp");
    expect(offerLine({ company: "Acme" })).toBeNull();
    expect(offerLine(null)).toBeNull();
  });
  it("keeps at most 6 reasons, most points first", () => {
    const reasons = Array.from({ length: 8 }, (_, i) => ({ source: "risk" as const, id: `r${i}`, label: `r${i}`, points: i % 3, link: "" }));
    const out = topReasons({ reasons } as Pick<RiskLevel, "reasons">);
    expect(out).toHaveLength(6);
    expect(out[0].points).toBe(2);
  });
  it("maps anchors to tabs", () => {
    expect(tabForHash("#redflag-RF03")).toBe("redflags");
    expect(tabForHash("#risk-r12")).toBe("risks");
    expect(tabForHash("#compare")).toBe("compare");
    expect(tabForHash("#nothing")).toBeNull();
  });
});
