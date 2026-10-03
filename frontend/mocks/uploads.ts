import { delay, http, HttpResponse } from "msw";
import type { Schemas } from "@/lib/api/client";
import { speed } from "./chat";

// Upload flow on mocks (B1.5). The scenario comes from the file name, so e2e tests and a person
// clicking around can reach every path:
//   *scan*  → scanned        *locked* → password      *notipo* → not_offer_document
//   *huge*  → too_many_pages  *drhp*  → a DRHP         *partial* → one stage fails
// Uploading the same bytes twice → "exists". The fourth upload in a session → quota.
// Synthetic data only; refresh from the fixture pack (B0.4) when B3.1 builds the report view.

type Doc = Schemas["DocRecord"];
interface MockDoc {
  doc: Doc;
  scenario: string;
  events: { event: string; data: unknown }[];
}

const docs = new Map<string, MockDoc>();
let uploadsToday = 0;
const PER_DAY = 3;

const err = (status: number, code: string, message: string, extra: Record<string, unknown> = {}) =>
  HttpResponse.json({ error: { code, message, ...extra } }, { status });

function scenarioOf(name: string): string {
  const n = name.toLowerCase();
  for (const s of ["scan", "locked", "notipo", "huge", "drhp", "partial"]) if (n.includes(s)) return s;
  return "rhp";
}

const REJECT: Record<string, string> = {
  scan: "scanned",
  locked: "password",
  notipo: "not_offer_document",
  huge: "too_many_pages",
};

function eventsFor(scenario: string): { event: string; data: unknown }[] {
  const st = (stage: string, status: "start" | "end" | "failed", detail?: Record<string, unknown>) => ({
    event: "stage",
    data: { stage, status, ...(detail ? { detail } : {}) },
  });
  const ev: { event: string; data: unknown }[] = [st("received", "end"), st("validated", "start")];
  if (REJECT[scenario]) {
    ev.push(st("validated", "failed", { reason: REJECT[scenario] }));
    ev.push({ event: "done", data: { status: "failed", failed_stages: ["validated"] } });
    return ev;
  }
  const type = scenario === "drhp" ? "drhp" : "rhp";
  ev.push(st("validated", "end", { ok: true }), st("detected", "start"));
  ev.push(st("detected", "end", { doc_type: type, company: "Acme Speciality Chemicals Limited", pages: 412 }));
  ev.push(st("parsed", "start"), { event: "progress", data: { stage: "parsed", done: 200, total: 412 } });
  ev.push(st("parsed", "end", { pages_done: 412, pages_total: 412 }), st("sections", "start"));
  ev.push(st("sections", "end", { found: ["risk_factors", "summary", "objects", "financials", "litigation"] }));
  ev.push(st("facts", "start"), st("facts", "end", { ready: true }), { event: "ready", data: { part: "facts" } });
  ev.push(st("financials", "start"), st("financials", "end", { ready: true }));
  const failed: string[] = [];
  if (scenario === "partial") {
    ev.push(st("redflags", "start"), st("redflags", "failed", { error: "RuntimeError" }));
    failed.push("redflags", "risk_level");
  } else {
    ev.push(st("redflags", "start"), st("redflags", "end", { ready: true, counts: { ok: 8, watch: 3, concern: 2 } }));
    ev.push({ event: "ready", data: { part: "redflags" } });
  }
  ev.push(st("risks_split", "start"), st("risks_split", "end", { n_risks: 64 }));
  ev.push(st("risks_scored", "start"), st("risks_scored", "end", { ready: true }), { event: "ready", data: { part: "risks" } });
  if (scenario === "partial") ev.push(st("risk_level", "failed", { skipped_because: ["redflags"] }));
  else ev.push(st("risk_level", "start"), st("risk_level", "end", { level: "medium" }), { event: "ready", data: { part: "risk_level" } });
  ev.push(st("simplify", "start"));
  for (let i = 1; i <= 15; i += 7) ev.push({ event: "progress", data: { stage: "simplify", done: i, total: 15 } });
  ev.push({ event: "progress", data: { stage: "simplify", done: 15, total: 15 } }, st("simplify", "end", { done: 15, total: 15 }));
  ev.push(st("index", "start"), st("index", "end", { ready: true }), { event: "ready", data: { part: "chat" } });
  ev.push({ event: "done", data: { status: failed.length ? "partial" : "ready", failed_stages: failed } });
  return ev;
}

function finalDoc(m: MockDoc): Doc {
  const last = m.events[m.events.length - 1].data as { status: Doc["status"] };
  const detected = m.events.find((e) => e.event === "stage" && (e.data as { stage: string; status: string }).stage === "detected" && (e.data as { status: string }).status === "end");
  const detail = (detected?.data as { detail?: { doc_type: Doc["doc_type"]; pages: number; company: string } } | undefined)?.detail;
  return {
    ...m.doc,
    status: last.status,
    rejection: (REJECT[m.scenario] ?? null) as Doc["rejection"],
    doc_type: detail?.doc_type ?? null,
    pages: detail?.pages ?? null,
    company: detail?.company ?? null,
  };
}

export const uploadHandlers = [
  http.get("/api/uploads/limits", () =>
    HttpResponse.json({ enabled: true, max_mb: 50, max_pages: 1500, per_user_per_day: PER_DAY }),
  ),
  http.post("/api/uploads/init", async ({ request }) => {
    if (!request.headers.get("Authorization")) return err(401, "unauthorized", "Please sign in with Google to upload.");
    const body = (await request.json()) as Schemas["UploadInit"];
    const docId = `doc_${body.sha256.slice(0, 16)}`;
    const existing = docs.get(docId);
    if (existing && existing.doc.status !== "uploading") return HttpResponse.json({ status: "exists", doc_id: docId });
    if (uploadsToday >= PER_DAY)
      return err(429, "quota_exceeded", "You've reached today's upload limit.", { limit: PER_DAY, resets_at: "2026-10-04T00:00:00+05:30" });
    uploadsToday += 1;
    const scenario = scenarioOf(body.filename);
    docs.set(docId, {
      scenario,
      events: eventsFor(scenario),
      doc: { doc_id: docId, sha256: body.sha256, created_at: new Date().toISOString(), status: "uploading", uploaded_by: "mock-user", is_showcase: false },
    });
    return HttpResponse.json({ status: "upload", doc_id: docId, upload_url: `/api/uploads/${docId}/file`, upload_method: "POST", expires_at: null });
  }),
  http.post("/api/uploads/:docId/file", async () => {
    await delay(300 * speed());
    return HttpResponse.json({ status: "stored" });
  }),
  http.post("/api/uploads/:docId/complete", ({ params }) => {
    const m = docs.get(String(params.docId));
    if (!m) return err(409, "upload_not_started", "Start the upload first.");
    m.doc = { ...m.doc, status: "processing" };
    return HttpResponse.json({ doc_id: m.doc.doc_id, job_id: `job_${m.doc.doc_id}`, status: "queued" });
  }),
  http.get("/api/docs/:docId", ({ params }) => {
    const m = docs.get(String(params.docId));
    if (!m) return err(404, "doc_not_found", "We couldn't find this report.");
    return HttpResponse.json({ doc: m.doc, job_id: `job_${m.doc.doc_id}`, stages: [], companion_doc_id: null });
  }),
  http.get("/api/docs/:docId/events", ({ params, request }) => {
    const m = docs.get(String(params.docId));
    if (!m) return err(404, "doc_not_found", "We couldn't find this report.");
    const after = Number(request.headers.get("Last-Event-ID") ?? 0);
    const enc = new TextEncoder();
    let i = after;
    const stream = new ReadableStream<Uint8Array>({
      async pull(controller) {
        if (i >= m.events.length) {
          m.doc = finalDoc(m);
          return controller.close();
        }
        const ev = m.events[i++];
        await new Promise((r) => setTimeout(r, 120 * speed()));
        const d = ev.data as { stage?: string; status?: string; detail?: { doc_type: Doc["doc_type"]; pages: number; company: string } };
        if (d.stage === "detected" && d.status === "end" && d.detail) {
          // Like the worker: the doc row learns its type, pages and company at `detected`.
          m.doc = { ...m.doc, doc_type: d.detail.doc_type, pages: d.detail.pages, company: d.detail.company };
        }
        controller.enqueue(enc.encode(`id: ${i}\nevent: ${ev.event}\ndata: ${JSON.stringify(ev.data)}\n\n`));
      },
    });
    return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" } });
  }),
  http.get("/api/me/uploads", ({ request }) => {
    if (!request.headers.get("Authorization")) return err(401, "unauthorized", "Please sign in.");
    return HttpResponse.json(
      [...docs.values()]
        .filter((m) => m.doc.status !== "uploading")
        .map((m) => ({ doc_id: m.doc.doc_id, company: m.doc.company ?? null, doc_type: m.doc.doc_type ?? null, created_at: m.doc.created_at, status: m.doc.status })),
    );
  }),
];
