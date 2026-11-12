import { describe, expect, it } from "vitest";
import { MOCK_SOD } from "@/mocks/sod";
import { byPeriod, cell, fyLabels, hasFinancials, parseSod, ratioText } from "./sod";

describe("parseSod", () => {
  it("returns null for missing or malformed input", () => {
    expect(parseSod(null)).toBeNull();
    expect(parseSod(undefined)).toBeNull();
    expect(parseSod("x")).toBeNull();
    expect(parseSod([])).toBeNull();
  });
  it("drops malformed rows instead of throwing", () => {
    const sod = parseSod({ financials: { revenue: [null, 3, { period: "latest", status: "found", value: null }], junk: "x" }, strengths: [{ heading: 1 }] });
    expect(sod?.financials.revenue).toHaveLength(1);
    expect(sod?.financials.junk).toBeUndefined();
    expect(sod?.strengths).toEqual([]);
    expect(hasFinancials(sod)).toBe(true);
  });
  it("reads the mock summary", () => {
    const sod = parseSod(MOCK_SOD);
    expect(sod?.strengths).toHaveLength(3);
    expect(sod?.promoter_holding_post).toBeNull();
    expect(fyLabels(sod!)).toEqual({ "latest-2": "FY2024", "latest-1": "FY2025", latest: "FY2026" });
  });
});

describe("cell and byPeriod", () => {
  const sod = parseSod(MOCK_SOD)!;
  it("formats money in the chosen unit and per-share figures in rupees", () => {
    const { fy } = byPeriod(sod.financials.revenue);
    expect(cell(fy.latest ?? null, "crore").text).toBe("₹1,398.00 crore");
    expect(cell(byPeriod(sod.financials.eps_basic).fy.latest ?? null, "crore", true).text).toBe("₹12.1");
  });
  it("treats any non-FY period as the stub and a not_found value as missing", () => {
    expect(byPeriod(sod.financials.eps_basic).stub?.period).toMatch(/June 30, 2026/);
    expect(cell(byPeriod(sod.financials.total_borrowings).stub, "crore").text).toBeNull();
  });
  it("puts the minus before the rupee sign", () => {
    expect(cell(byPeriod(sod.financials.operating_cash_flow).fy["latest-1"] ?? null, "crore").text).toBe("−₹12.00 crore");
  });
});

describe("ratioText", () => {
  it("formats computed ratios and hides unavailable ones", () => {
    const [growth, , de, ocf] = parseSod(MOCK_SOD)!.derived;
    expect(ratioText(growth, "crore")).toBe("22.1%");
    expect(ratioText(de, "crore")).toBe("0.31×");
    expect(ratioText(ocf, "crore")).toBeNull();
  });
});
