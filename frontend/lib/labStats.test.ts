import { describe, expect, it } from "vitest";
import { detectionPct, robustPct } from "./labStats";

describe("labStats", () => {
  it("reads detection from a nested summary", () => {
    expect(detectionPct({ summary: { detection: { rate: 0.995, n: 200 } } })).toBe(100);
    expect(detectionPct({ detection: { rate: 0.875 } })).toBe(88);
  });
  it("returns null when missing or malformed", () => {
    expect(detectionPct({})).toBeNull();
    expect(detectionPct(undefined)).toBeNull();
    expect(detectionPct({ detection: { rate: null } })).toBeNull();
    expect(robustPct({ ladder: {} })).toBeNull();
  });
  it("reads fine-tuned body-only accuracy on the headline split", () => {
    const ladder = { headline_split: "test", ladder: { qa_finetuned: { test: { body_only: { nvm: 0.85 } } } } };
    expect(robustPct(ladder)).toBe(85);
  });
});
