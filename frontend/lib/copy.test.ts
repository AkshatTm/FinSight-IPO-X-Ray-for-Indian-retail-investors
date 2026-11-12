import { describe, expect, it } from "vitest";
import { errorMessage, STRINGS, t } from "./copy";

const BANNED = [
  "revolutionary", "seamless", "unlock", "empower", "leverage", "cutting-edge",
  "game-changer", "effortless", "magic", "supercharge", "delve", "robust", "elevate",
];

describe("copy dictionary", () => {
  const entries = Object.entries(STRINGS) as [string, string][];

  it("has text for every key", () => {
    for (const [k, v] of entries) expect(v.trim(), k).not.toBe("");
  });
  it("uses no banned words, exclamation marks or emoji", () => {
    for (const [k, v] of entries) {
      expect(v, k).not.toMatch(/!/);
      expect(v, k).not.toMatch(/\p{Extended_Pictographic}/u);
      // Whole words: the marketing verb "unlock" is banned, B05's "an unlocked copy" (a PDF) is not.
      for (const w of BANNED) expect(v.toLowerCase(), k + ": " + w).not.toMatch(new RegExp("\\b" + w + "\\b"));
    }
  });
  it("has no Devanagari text", () => {
    for (const [k, v] of entries) expect(v, k).not.toMatch(/[\u0900-\u097F]/);
  });
  it("interpolates", () => {
    expect(t("reason.verified", { doc: "RHP", page: 3 })).toBe(
      "This number is in the document, for the same item, on RHP page 3.",
    );
    expect(t("meter.some", { v: 2, n: 3, u: 1 })).toBe("2 of 3 numbers match. 1 couldn't be checked.");
  });
  it("maps API error codes, unknown codes fall back", () => {
    expect(errorMessage("ipo_not_found")).toBe("We couldn't find that IPO.");
    expect(errorMessage("network")).toContain("Vidura");
    expect(errorMessage("something_new")).toBe("Something went wrong on our side. Try again.");
  });
});
