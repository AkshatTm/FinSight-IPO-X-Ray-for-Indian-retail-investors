import { describe, expect, it } from "vitest";
import { applyJobEvent, EMPTY_JOB, rowState, toJobEvent, type JobEvent } from "./jobs";
import { SseParser } from "./sse";

const fold = (events: JobEvent[]) => events.reduce((v, ev, i) => applyJobEvent(v, ev, 1000 * (i + 1)), EMPTY_JOB);

describe("job events", () => {
  it("parses id, event and data from the stream", () => {
    const [raw] = new SseParser().push('id: 7\nevent: ready\ndata: {"part":"facts"}\n\n');
    expect(toJobEvent(raw)).toEqual({ event: "ready", data: { part: "facts" }, id: 7 });
    expect(toJobEvent({ event: "token", data: "{}" })).toBeNull();
  });

  it("folds stages into rows with timings", () => {
    const v = fold([
      { event: "stage", data: { stage: "detected", status: "start", detail: null }, id: 1 },
      { event: "stage", data: { stage: "detected", status: "end", detail: { doc_type: "rhp", pages: 412 } }, id: 2 },
      { event: "stage", data: { stage: "financials", status: "start", detail: null }, id: 3 },
      { event: "stage", data: { stage: "financials", status: "end", detail: null }, id: 4 },
    ]);
    expect(v.lastId).toBe(4);
    expect(v.stages.detected).toMatchObject({ status: "done", ms: 1000, detail: { pages: 412 } });
    expect(rowState(v, ["detected"])).toBe("done");
    expect(rowState(v, ["financials", "redflags"])).toBe("running"); // one of two stages done
    expect(rowState(v, ["index"])).toBe("waiting");
  });

  it("marks failed rows and records ready parts and done", () => {
    const v = fold([
      { event: "stage", data: { stage: "redflags", status: "failed", detail: { error: "RuntimeError" } } },
      { event: "ready", data: { part: "facts" } },
      { event: "ready", data: { part: "facts" } },
      { event: "progress", data: { stage: "simplify", done: 3, total: 15 } },
      { event: "done", data: { status: "partial", failed_stages: ["redflags"] } },
    ]);
    expect(rowState(v, ["financials", "redflags"])).toBe("failed");
    expect(v.ready).toEqual(["facts"]);
    expect(v.progress.simplify).toEqual({ done: 3, total: 15 });
    expect(v.done?.status).toBe("partial");
  });
});
