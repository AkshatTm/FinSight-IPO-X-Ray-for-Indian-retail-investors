import fc from "fast-check";
import { describe, expect, it } from "vitest";
import {
  formatDate,
  formatMoney,
  formatMonthYear,
  formatPercent,
  formatRupee,
  formatShares,
  fractionPercent,
  groupDigits,
} from "./format";

describe("groupDigits", () => {
  it("groups Indian style", () => {
    expect(groupDigits("999", "indian")).toBe("999");
    expect(groupDigits("1000", "indian")).toBe("1,000");
    expect(groupDigits("262600", "indian")).toBe("2,62,600");
    expect(groupDigits("11051746", "indian")).toBe("1,10,51,746");
    expect(groupDigits("26260000000", "indian")).toBe("26,26,00,00,000");
  });
  it("groups Western style", () => {
    expect(groupDigits("26260", "western")).toBe("26,260");
    expect(groupDigits("11051746", "western")).toBe("11,051,746");
  });
  it("removing commas gives the digits back (property)", () => {
    fc.assert(
      fc.property(fc.bigInt({ min: BigInt(0), max: BigInt("1000000000000000000") }), (n) => {
        const s = n.toString();
        expect(groupDigits(s, "indian").replace(/,/g, "")).toBe(s);
        expect(groupDigits(s, "western").replace(/,/g, "")).toBe(s);
      }),
    );
  });
});

describe("formatMoney (spec 15)", () => {
  const v = "26260000000"; // 26,260 million
  it("crore", () => expect(formatMoney(v, "crore")).toBe("₹2,626.00 crore"));
  it("million", () => expect(formatMoney(v, "million")).toBe("₹26,260.00 million"));
  it("lakh", () => expect(formatMoney(v, "lakh")).toBe("₹2,62,600.00 lakh"));
  it("full", () => expect(formatMoney(v, "full")).toBe("₹26,26,00,00,000"));
  it("keeps fractions without float error", () => {
    expect(formatMoney("1234567.89", "crore")).toBe("₹0.12 crore");
    expect(formatMoney("8000000000", "crore")).toBe("₹800.00 crore");
    expect(formatMoney("8000000000", "million")).toBe("₹8,000.00 million");
    expect(formatMoney("80000000", "crore")).toBe("₹8.00 crore");
  });
  it("rounds half up at 2 decimals", () => {
    expect(formatMoney("100500000", "crore")).toBe("₹10.05 crore");
    expect(formatMoney("100550000", "crore")).toBe("₹10.06 crore");
  });
  it("accepts numbers and zero", () => {
    expect(formatMoney(0, "crore")).toBe("₹0.00 crore");
    expect(formatMoney(8e9, "crore")).toBe("₹800.00 crore");
  });
  it("rejects garbage", () => {
    expect(() => formatMoney("abc", "crore")).toThrow();
  });
  it("crore view of n * 10^7 round-trips (property)", () => {
    fc.assert(
      fc.property(fc.bigInt({ min: BigInt(0), max: BigInt("100000000000000") }), (n) => {
        const out = formatMoney((n * BigInt(10000000)).toString(), "crore");
        const back = out.replace(/[₹,]|\scrore/g, "");
        expect(back).toBe(`${n}.00`);
      }),
    );
  });
});

describe("shares, rupee, percent, dates", () => {
  it("shares", () => {
    expect(formatShares("11051746", "as-written")).toBe("11,051,746 shares");
    expect(formatShares("11051746", "indian")).toBe("1,10,51,746 shares");
    expect(formatShares(11051746, "indian", "hi")).toBe("1,10,51,746 शेयर");
  });
  it("rupee per share keeps printed precision", () => {
    expect(formatRupee("321")).toBe("₹321");
    expect(formatRupee("1250.50")).toBe("₹1,250.5");
    expect(formatRupee("2")).toBe("₹2");
  });
  it("percent one decimal", () => {
    expect(formatPercent(64)).toBe("64.0%");
    expect(formatPercent(36.04)).toBe("36.0%");
    expect(formatPercent(99.95)).toBe("100.0%");
  });
  it("fractionPercent", () => {
    expect(fractionPercent(25, 100)).toBe(25);
    expect(fractionPercent(1, 0)).toBeNull();
  });
  it("dates", () => {
    expect(formatDate("2025-11-12")).toBe("12 Nov 2025");
    expect(formatDate("2025-11-12", "hi")).toBe("12 नवंबर 2025");
    expect(formatDate("2025-01-05T00:00:00Z", "hi")).toBe("5 जनवरी 2025");
    expect(formatMonthYear("2025-11-12", "hi")).toBe("नवंबर 2025");
    expect(() => formatDate("12/11/2025")).toThrow();
  });
});
