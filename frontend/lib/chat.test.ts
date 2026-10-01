import { describe, expect, it } from "vitest";
import {
  applyEvent, comparison, copyText, factorText, guardKind, meter, meterText,
  newTurn, reasonText, segmentAnswer, type Verdict,
} from "./chat";

const money = (inr: string, raw: string) => ({ kind: "money" as const, value_inr: inr, currency: "INR" as const, raw, scale_word: null, precision: 2 });

const scale: Verdict = {
  index: 0,
  answer_char_span: [24, 35],
  answer_value: money("2626000000", "₹26,260 lakh"),
  status: "contradicted",
  reason_code: "scale_mismatch",
  reason: "api reason",
  evidence: { passage_id: "p1", doc: "rhp", page: 3, char_span: [10, 30], bbox: [72, 410, 301, 423], value: money("26260000000", "₹26,260 million") },
};

describe("applyEvent", () => {
  it("builds a turn from a stream", () => {
    let t = newTurn("1", "x", "q", "en");
    t = applyEvent(t, { event: "stage", data: { name: "guard", status: "start", ms: null } }, 100);
    expect(t.stage).toEqual({ name: "guard", startedAt: 100 });
    t = applyEvent(t, { event: "token", data: { text: "The " } });
    t = applyEvent(t, { event: "token", data: { text: "fresh" } });
    expect(t.streamed).toBe("The fresh");
    t = applyEvent(t, { event: "answer", data: { text: "The fresh issue", citations: [] } });
    expect(t.streamed).toBe("The fresh issue");
    t = applyEvent(t, { event: "verdict", data: { ...scale, index: 1 } });
    t = applyEvent(t, { event: "verdict", data: scale });
    expect(t.verdicts.map((v) => v.index)).toEqual([0, 1]);
    t = applyEvent(t, { event: "final", data: { trace_id: "t", score: 0, n_numbers: 2, timings_ms: {} } });
    expect(t.status).toBe("done");
    expect(t.stage).toBeNull();
  });
  it("marks errors", () => {
    const t = applyEvent(newTurn("1", "x", "q", "en"), { event: "error", data: { code: "llm_unavailable", message: "m" } });
    expect(t.status).toBe("error");
    expect(t.error?.code).toBe("llm_unavailable");
  });
});

describe("guardKind", () => {
  it("maps reasons to cards", () => {
    expect(guardKind("privacy")).toBe("privacy");
    expect(guardKind("forecast")).toBe("forecast");
    expect(guardKind("advice_intent")).toBe("advice");
    expect(guardKind("gmp")).toBe("advice");
    expect(guardKind("rating")).toBe("advice");
  });
});

describe("faithfulness meter wording (13.2)", () => {
  const v = (status: Verdict["status"], i: number): Verdict => ({ ...scale, index: i, status });
  it("covers all, some unchecked, any contradicted, and none", () => {
    expect(meterText([], "en")).toBe("No numbers to check in this answer.");
    expect(meterText([v("verified", 0), v("verified", 1)], "en")).toBe("2 of 2 numbers match the document");
    expect(meterText([v("verified", 0), v("unverifiable", 1)], "en")).toBe("1 of 2 numbers match. 1 couldn't be checked.");
    expect(meterText([v("verified", 0), v("contradicted", 1)], "en")).toBe("1 number(s) don't match the document. Check the marked ones.");
    expect(meter([v("verified", 0), v("unverifiable", 1), v("contradicted", 2)])).toEqual({ n: 3, v: 1, u: 1, c: 1 });
  });
});

describe("segmentAnswer", () => {
  const text = "Yes, the fresh issue is ₹26,260 lakh [1].";
  it("splits numbers and citations in order", () => {
    const s = text.indexOf("₹");
    const segs = segmentAnswer(text, [{ ...scale, answer_char_span: [s, s + 12] }], [{ n: 1, char_start: text.indexOf("[1]"), char_end: text.indexOf("[1]") + 3 }]);
    expect(segs.map((x) => x.type)).toEqual(["text", "number", "text", "cite", "text"]);
    expect(segs.map((x) => x.text).join("")).toBe(text);
  });
  it("ignores spans outside the text or overlapping", () => {
    const segs = segmentAnswer("abc", [{ ...scale, answer_char_span: [2, 99] }, { ...scale, index: 1, answer_char_span: [0, 2] }, { ...scale, index: 2, answer_char_span: [1, 3] }], []);
    expect(segs.map((x) => x.text).join("")).toBe("abc");
    expect(segs.filter((x) => x.type === "number")).toHaveLength(1);
  });
});

describe("reasons and comparison (13.1)", () => {
  it("explains a unit slip with both values in crore and the factor", () => {
    expect(reasonText(scale, "en")).toBe(
      "Wrong unit. The answer says ₹26,260 lakh (₹262.60 crore). The document says ₹26,260 million (₹2,626.00 crore). That's 10 times different.",
    );
    expect(reasonText(scale, "hi")).toContain("10 गुना");
  });
  it("uses the template for verified and falls back to the API text for wrong_value", () => {
    expect(reasonText({ ...scale, status: "verified", reason_code: "verified" }, "en")).toBe(
      "This number is in the document, for the same item, on RHP page 3.",
    );
    expect(reasonText({ ...scale, reason_code: "wrong_value" }, "en")).toBe("api reason");
  });
  it("compares as written, in crore and in million", () => {
    const c = comparison(scale, "en");
    expect(c.asWritten).toEqual(["₹26,260 lakh", "₹26,260 million"]);
    expect(c.crore).toEqual(["₹262.60 crore", "₹2,626.00 crore"]);
    expect(c.million).toEqual(["₹2,626.00 million", "₹26,260.00 million"]);
  });
  it("factorText", () => {
    expect(factorText(8e7, 8e9)).toBe("100");
    expect(factorText(100, 250)).toBe("2.5");
    expect(factorText(0, 5)).toBe("");
  });
});

describe("copyText", () => {
  it("adds page references for the cited passages", () => {
    const t = {
      ...newTurn("1", "x", "q", "en"),
      answer: { text: "Answer [1]", citations: [{ n: 1, char_start: 7, char_end: 10 }] },
      retrieval: { dropped: [], passages: [{ n: 1, id: "p", doc: "rhp" as const, page_start: 120, page_end: 120, section: "s", snippet: "", bm25_rank: null, dense_rank: null, fused_rank: null, rerank_score: null }] },
    };
    expect(copyText(t)).toBe("Answer [1]\n\n[1] RHP p.120");
  });
});
