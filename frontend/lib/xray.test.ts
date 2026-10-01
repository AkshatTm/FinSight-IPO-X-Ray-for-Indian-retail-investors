import { describe, expect, it } from "vitest";
import { buildXray } from "@/mocks/xray";
import { fieldById, parseObjectsTable, resolveField, scalarText, sentenceAround } from "./xray";

describe("resolveField", () => {
  const x = buildXray("ather-energy-2025")!;
  it("prefers the prospectus value when the RHP is blank", () => {
    const r = resolveField(fieldById(x.fields, "offer_price")!);
    expect(r.filledInProspectus).toBe(true);
    expect(r.doc).toBe("prospectus");
  });
  it("keeps the RHP value when present", () => {
    const r = resolveField(fieldById(x.fields, "face_value")!);
    expect(r.doc).toBe("rhp");
    expect(r.filledInProspectus).toBe(false);
  });
  it("flags a blank placeholder with no companion, and not-in-document", () => {
    const f = fieldById(x.fields, "price_band")!;
    expect(resolveField(f).blank).toBe(true);
    const pure = buildXray("lg-electronics-india-2025")!;
    expect(resolveField(fieldById(pure.fields, "fresh_issue_size")!).notInDocument).toBe(true);
  });
});

describe("scalarText", () => {
  it("formats money in the chosen unit and per-share prices without a unit", () => {
    const m = { kind: "money" as const, value_inr: "26260000000", currency: "INR" as const, raw: "x", scale_word: null, precision: 2 };
    expect(scalarText("fresh_issue_size", m, "crore", "en", "per share")).toBe("₹2,626.00 crore");
    expect(scalarText("fresh_issue_size", m, "million", "hi", "प्रति शेयर")).toBe("₹26,260.00 मिलियन");
    expect(scalarText("face_value", { ...m, value_inr: "1" }, "crore", "en", "per share")).toBe("₹1");
  });
  it("formats share counts with Indian grouping", () => {
    expect(scalarText("ofs_shares", { kind: "count", value: 11051746, raw: "11,051,746", unit: "shares" }, "crore", "en", "")).toBe("1,10,51,746 shares");
  });
});

describe("sentenceAround", () => {
  const w = (t: string, x0: number, x1: number, y = 410) => ({ t, b: [x0, y, x1, y + 12] as [number, number, number, number] });
  it("joins the words of the line and marks the ones inside the box", () => {
    const words = [w("Fresh", 72, 95), w("Issue", 98, 120), w("₹26,260", 125, 170), w("million", 173, 210), w("Other", 72, 100, 500)];
    const s = sentenceAround(words, [120, 410, 215, 422]);
    expect(s.text).toBe("Fresh Issue ₹26,260 million");
    expect(s.parts.filter((p) => p.hit).map((p) => p.text)).toEqual(["₹26,260", "million"]);
  });
});

describe("parseObjectsTable", () => {
  it("reads amounts with the unit from the column header", () => {
    const rows = parseObjectsTable({
      kind: "table",
      columns: ["Object", "Amount (₹ million)"],
      rows: [["Capex", "20,000.00"], ["Product development", "6,000"], ["General corporate purposes", "[●]"]],
    });
    expect(rows[0].inr).toBe("20000000000");
    expect(rows[1].inr).toBe("6000000000");
    expect(rows[2].inr).toBeNull();
  });
  it("leaves amounts unconverted when the header has no unit", () => {
    const rows = parseObjectsTable({ kind: "table", columns: ["Object", "Amount"], rows: [["A", "100"]] });
    expect(rows[0].inr).toBeNull();
  });
});
