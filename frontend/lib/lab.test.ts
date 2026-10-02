import { describe, expect, it } from "vitest";
import { LAB_ASR, LAB_LADDER, LAB_RETRIEVAL, LAB_VERIFIER, LAB_WEAKLABELS } from "@/mocks/lab";
import { asrStats, heatmap, ladderRows, ladderSize, ladderTakeaway, retrievalRows, verifierStats, weakStats } from "./lab";

describe("ladder", () => {
  it("lists rungs in order with both columns", () => {
    const rows = ladderRows(LAB_LADDER);
    expect(rows.map((r) => r.key)).toEqual(["rules", "qa_pretrained", "qa_finetuned"]);
    expect(rows[0].full.nvm).toBe(0.8571);
    expect(rows[0].body.n).toBe(35);
  });
  it("adds an unknown rung (BiLSTM-CRF) after the known ones", () => {
    const withBilstm = structuredClone(LAB_LADDER) as typeof LAB_LADDER & { ladder: Record<string, unknown> };
    withBilstm.ladder.bilstm = { label: "BiLSTM-CRF", test: LAB_LADDER.ladder.rules.test };
    expect(ladderRows(withBilstm).at(-1)?.label).toBe("BiLSTM-CRF");
  });
  it("fills the takeaway from the numbers, never from text", () => {
    expect(ladderTakeaway(LAB_LADDER)).toEqual({ rulesBody: 23, ftBody: 85, delta: 38 });
    expect(ladderSize(LAB_LADDER)).toEqual({ n: 56, k: 7 });
  });
  it("builds the fact-by-method grid", () => {
    const h = heatmap(LAB_LADDER)!;
    expect(h.rows.map((r) => r.key)).toEqual(["rules", "qa_pretrained", "qa_finetuned"]);
    expect(h.fields).toHaveLength(8);
    expect(h.rows[0].cells.fresh_issue_size).toBe(1);
  });
  it("returns nothing for missing or malformed data", () => {
    expect(ladderRows(undefined)).toEqual([]);
    expect(ladderRows({ ladder: { rules: {} } })).toEqual([]);
    expect(ladderTakeaway({})).toBeNull();
    expect(heatmap({})).toBeNull();
  });
});

describe("weak labels, verifier, retrieval, asr", () => {
  it("reads the audit with its range", () => {
    expect(weakStats(LAB_WEAKLABELS)).toEqual({ examples: 4538, ipos: 389, precision: 90, lo: 79, hi: 96 });
    expect(weakStats({ n_ipos: 3 })).toBeNull();
  });
  it("reads caught, false alarms, unit mix-ups and merges the two unit error types", () => {
    const v = verifierStats(LAB_VERIFIER)!;
    expect(v.caught).toEqual({ hits: 100, n: 100 });
    expect(v.falseAlarms).toEqual({ hits: 0, n: 100 });
    expect(v.unit).toEqual({ hits: 35, n: 40 });
    expect(v.unitFixed).toEqual({ hits: 40, n: 40 });
    expect(v.types.find((t) => t.key === "scale")).toEqual({ key: "scale", n: 40, ok: 40 });
    expect(v.types.map((t) => t.key)).toEqual(["digit", "scale", "swap_metric", "invented", "rounding_ok", "correct"]);
    expect(verifierStats({})).toBeNull();
  });
  it("lists retrieval methods with Hindi recall and abstention", () => {
    const rows = retrievalRows(LAB_RETRIEVAL);
    expect(rows.map((r) => r.key)).toEqual(["bm25", "dense", "hybrid", "hybrid+rerank"]);
    expect(rows[3]).toEqual({ key: "hybrid+rerank", recall5: 0.6071, hiRecall5: 0.5556, abstained: "9/11" });
    expect(retrievalRows({})).toEqual([]);
  });
  it("reports the full-profile ASR error in percent", () => {
    expect(asrStats(LAB_ASR)).toEqual({ cer: 6.2, clips: 10 });
    expect(asrStats({})).toBeNull();
  });
});
