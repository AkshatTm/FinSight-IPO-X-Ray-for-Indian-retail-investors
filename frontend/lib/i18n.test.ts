import { describe, expect, it } from "vitest";
import { errorMessage, STRINGS, t } from "./i18n";

const BANNED = [
  "revolutionary", "seamless", "unlock", "empower", "leverage", "cutting-edge",
  "game-changer", "effortless", "magic", "supercharge", "delve", "robust", "elevate",
];

describe("i18n dictionary", () => {
  const entries = Object.entries(STRINGS);

  it("has EN and HI for every key", () => {
    for (const [k, v] of entries) {
      expect(v.en.trim(), k).not.toBe("");
      expect(v.hi.trim(), k).not.toBe("");
    }
  });
  it("uses no banned words, exclamation marks or emoji (spec 1.4)", () => {
    for (const [k, v] of entries) {
      for (const text of [v.en, v.hi]) {
        expect(text, k).not.toMatch(/!/);
        expect(text, k).not.toMatch(/\p{Extended_Pictographic}/u);
      }
      for (const w of BANNED) expect(v.en.toLowerCase(), `${k}: ${w}`).not.toContain(w);
    }
  });
  it("keeps Hindi numerals Western (no Devanagari digits)", () => {
    for (const [k, v] of entries) expect(v.hi, k).not.toMatch(/[०-९]/);
  });
  it("uses the same placeholders in EN and HI", () => {
    const vars = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    for (const [k, v] of entries) expect(vars(v.hi), k).toEqual(vars(v.en));
  });
  it("interpolates", () => {
    expect(t("reason.verified", "en", { doc: "RHP", page: 3 })).toBe(
      "This number is in the document, for the same item, on RHP page 3.",
    );
    expect(t("meter.some", "hi", { v: 2, n: 3, u: 1 })).toBe("3 में से 2 आंकड़े मेल खाते हैं। 1 की जाँच नहीं हो सकी।");
  });
  it("maps API error codes, unknown codes fall back", () => {
    expect(errorMessage("ipo_not_found", "en")).toBe("We couldn't find that IPO.");
    expect(errorMessage("network", "hi")).toContain("FinSight");
    expect(errorMessage("something_new", "en")).toBe("Something went wrong on our side. Try again.");
  });
});
