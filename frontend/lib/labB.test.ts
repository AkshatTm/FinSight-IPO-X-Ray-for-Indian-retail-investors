import { describe, expect, it } from "vitest";
import { classifierLadder, financialChecks, novelty, outcomes, rewrites, risksExplained, segmentation, speedCost, strength } from "./labB";

describe("Phase 2 Lab readers", () => {
  it("return null or empty when a file is missing or malformed", () => {
    for (const v of [undefined, null, {}, { f1: "0.9" }]) {
      expect(segmentation(v)).toBeNull();
      expect(financialChecks(v, v)).toBeNull();
      expect(classifierLadder(v)).toEqual([]);
      expect(rewrites(v, v)).toBeNull();
      expect(novelty(v)).toBeNull();
      expect(outcomes(v)).toEqual([]);
      expect(speedCost(v, v)).toBeNull();
      expect(risksExplained(v)).toBeNull();
    }
  });

  it("orders the classifier ladder TF-IDF, base, large, teacher and reads gold before dev", () => {
    const rows = classifierLadder({
      systems: [
        { file: "classifier_teacher", model: "teacher zero-shot", gold: { macro_f1: 0.71, n: 150 } },
        { file: "classifier_deberta_large", model: "large", gold: { macro_f1: 0.66, n: 150 } },
        { file: "classifier_tfidf", model: "tfidf-logreg", dev: { macro_f1: 0.5, n: 900 }, gold: { macro_f1: 0.48, n: 150 } },
        { file: "classifier_deberta_base", model: "base", macro_f1_mean: 0.6, macro_f1_std: 0.02, seeds: [1, 2, 3], gold: { macro_f1: 0.61, n: 150 } },
      ],
    });
    expect(rows.map((r) => r.key)).toEqual(["tfidf", "deberta_base", "deberta_large", "teacher"]);
    expect(rows[0]).toMatchObject({ f1: 0.48, n: 150 });
    expect(rows[1]).toMatchObject({ f1: 0.6, std: 0.02, seeds: 3 });
  });

  it("never calls a relationship stronger than moderate, and 'no clear' when the range crosses 0", () => {
    expect(strength(-0.45, -0.6, -0.3)).toBe("moderate");
    expect(strength(0.9, 0.8, 0.95)).toBe("moderate");
    expect(strength(-0.15, -0.28, -0.02)).toBe("weak");
    expect(strength(-0.2, -0.35, 0.01)).toBe("none");
  });

  it("reads rewrite checks, readability and the risks-explained count", () => {
    const simplify = { human: { systems: [{ system: "student", yes: 30, partly: 15, no: 5, n: 50 }] }, checks: { n: 400, rejected: 40, reasons: { numbers: 25, certainty: 15 } } };
    const r = rewrites(simplify, { fkgl_original: 16.2, fkgl_rewrite: 9.1 });
    expect(r?.rejected).toBeCloseTo(0.1);
    expect(r?.gradeDrop).toBeCloseTo(7.1);
    expect(r?.reasons.map((x) => x.key)).toEqual(["numbers", "certainty"]);
    expect(risksExplained(simplify)).toBe(360);
  });

  it("keeps the chosen novelty cut-off and sorts by it", () => {
    expect(novelty({ chosen_tau: 0.8, points: [{ tau: 0.85, precision: 0.9, n: 20 }, { tau: 0.75, precision: 0.6, n: 20 }] })).toEqual({
      chosen: 0.8,
      points: [{ tau: 0.75, precision: 0.6, n: 20 }, { tau: 0.85, precision: 0.9, n: 20 }],
    });
  });
});
