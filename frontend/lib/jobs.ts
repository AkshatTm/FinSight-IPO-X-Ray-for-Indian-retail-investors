import type { Schemas } from "@/lib/api/client";
import { ApiError } from "@/lib/api/client";
import { SseParser, type RawSse } from "@/lib/sse";

type S = Schemas;

/** Typed events of GET /api/docs/{doc_id}/events (B06 §2). */
export type JobEvent =
  | { event: "stage"; data: S["JobStageEvent"]; id?: number }
  | { event: "progress"; data: S["JobProgressEvent"]; id?: number }
  | { event: "ready"; data: S["JobReadyEvent"]; id?: number }
  | { event: "risk_simplified"; data: S["RiskSimplifiedEvent"]; id?: number }
  | { event: "done"; data: S["JobDoneEvent"]; id?: number };

const KNOWN = new Set(["stage", "progress", "ready", "risk_simplified", "done"]);

export function toJobEvent(m: RawSse): JobEvent | null {
  if (!KNOWN.has(m.event)) return null;
  try {
    const ev = { event: m.event, data: JSON.parse(m.data) } as JobEvent;
    if (m.id && /^\d+$/.test(m.id)) ev.id = Number(m.id);
    return ev;
  } catch {
    return null;
  }
}

/** The processing screen's rows (B05 §4): a row is done when all its stages are done. */
export const ROWS = [
  { key: "detected", stages: ["detected"] },
  { key: "parsed", stages: ["parsed"] },
  { key: "sections", stages: ["sections"] },
  { key: "facts", stages: ["facts"] },
  { key: "redflags", stages: ["financials", "redflags"] },
  { key: "risks", stages: ["risks_split", "risks_scored"] },
  { key: "risk_level", stages: ["risk_level"] },
  { key: "simplify", stages: ["simplify"] },
  { key: "index", stages: ["index"] },
] as const;
export type RowKey = (typeof ROWS)[number]["key"];
export type RowState = "waiting" | "running" | "done" | "failed";

export interface StageInfo {
  status: "running" | "done" | "failed";
  detail: Record<string, unknown> | null;
  startedAt: number | null;
  ms: number | null;
}

export interface JobView {
  stages: Record<string, StageInfo>;
  ready: string[];
  progress: Record<string, { done: number; total: number }>;
  done: S["JobDoneEvent"] | null;
  lastId: number;
}

export const EMPTY_JOB: JobView = { stages: {}, ready: [], progress: {}, done: null, lastId: 0 };

/** Fold one event into the view (pure; `now` is injectable for tests). */
export function applyJobEvent(view: JobView, ev: JobEvent, now = Date.now()): JobView {
  const next: JobView = { ...view, lastId: Math.max(view.lastId, ev.id ?? view.lastId) };
  switch (ev.event) {
    case "stage": {
      const prev = view.stages[ev.data.stage];
      const detail = (ev.data.detail ?? null) as Record<string, unknown> | null;
      const info: StageInfo =
        ev.data.status === "start"
          ? { status: "running", detail: null, startedAt: now, ms: null }
          : {
              status: ev.data.status === "end" ? "done" : "failed",
              detail,
              startedAt: prev?.startedAt ?? null,
              ms: prev?.startedAt != null ? now - prev.startedAt : null,
            };
      next.stages = { ...view.stages, [ev.data.stage]: info };
      break;
    }
    case "progress":
      next.progress = { ...view.progress, [ev.data.stage]: { done: ev.data.done, total: ev.data.total } };
      break;
    case "ready":
      next.ready = view.ready.includes(ev.data.part) ? view.ready : [...view.ready, ev.data.part];
      break;
    case "done":
      next.done = ev.data;
      break;
    default:
      break;
  }
  return next;
}

/** A row's state from its stages; rows whose stages never ran stay "waiting". */
export function rowState(view: JobView, stages: readonly string[]): RowState {
  const infos = stages.map((s) => view.stages[s]).filter(Boolean);
  if (infos.some((i) => i.status === "failed")) return "failed";
  if (infos.length === stages.length && infos.every((i) => i.status === "done")) return "done";
  if (infos.length) return "running";
  return "waiting";
}

/** Follow a job's events; reconnects with Last-Event-ID until `done` (or the signal aborts). */
export async function* followJob(docId: string, signal: AbortSignal, after = 0): AsyncGenerator<JobEvent> {
  let last = after;
  for (let attempt = 0; attempt < 30 && !signal.aborted; attempt++) {
    let res: Response;
    try {
      res = await fetch(`/api/docs/${docId}/events`, {
        headers: { Accept: "text/event-stream", ...(last ? { "Last-Event-ID": String(last) } : {}) },
        signal,
      });
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      await new Promise((r) => setTimeout(r, 1000));
      continue;
    }
    if (!res.ok || !res.body) throw new ApiError(res.status === 404 ? "doc_not_found" : "internal_error", res.statusText, res.status);
    const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
    const parser = new SseParser();
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        for (const raw of parser.push(value)) {
          const ev = toJobEvent(raw);
          if (!ev) continue;
          if (ev.id) last = ev.id;
          yield ev;
          if (ev.event === "done") return;
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
    }
  }
}
