import { http, HttpResponse, delay } from "msw";
import { adminHandlers } from "./admin";
import { DETAILS, HEALTH, IPOS } from "./fixtures";
import { LAB_ASR, LAB_LADDER, LAB_RETRIEVAL, LAB_VERIFIER, LAB_WEAKLABELS } from "./lab";
import { scenario, speed } from "./chat";
import { pageSvg, pageWords } from "./pages";
import { reportHandlers } from "./report";
import { uploadHandlers } from "./uploads";
import { buildXray, SUGGESTED } from "./xray";

const notFound = () =>
  HttpResponse.json(
    { error: { code: "ipo_not_found", message: "IPO not found" } },
    { status: 404 },
  );

export const handlers = [
  ...reportHandlers, // before uploads: the sample report's /api/docs/<id> wins
  ...uploadHandlers,
  ...adminHandlers,
  http.get("/api/health", () => HttpResponse.json(HEALTH)),
  http.get("/api/ipos", async () => {
    await delay(150);
    return HttpResponse.json(IPOS);
  }),
  http.get("/api/ipos/:id", ({ params }) => {
    const d = DETAILS[String(params.id)];
    return d ? HttpResponse.json(d) : notFound();
  }),
  http.get("/api/ipos/:id/xray", async ({ params }) => {
    await delay(120);
    const x = buildXray(String(params.id));
    return x ? HttpResponse.json(x) : notFound();
  }),
  http.get("/api/ipos/:id/suggested-questions", ({ params }) =>
    DETAILS[String(params.id)] ? HttpResponse.json(SUGGESTED) : notFound(),
  ),
  http.get("/api/ipos/:id/pages/:n", ({ params, request }) => {
    const d = DETAILS[String(params.id)];
    if (!d) return notFound();
    const doc = new URL(request.url).searchParams.get("doc") ?? "rhp";
    const total = doc === "prospectus" ? (d.prospectus_pages ?? d.rhp_pages) : d.rhp_pages;
    const n = Number(params.n);
    if (!(n >= 1 && n <= total))
      return HttpResponse.json({ error: { code: "page_out_of_range", message: "Page out of range" } }, { status: 404 });
    return new HttpResponse(pageSvg(d.company, doc, n, total), {
      headers: { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=31536000, immutable" },
    });
  }),
  http.get("/api/ipos/:id/pages/:n/words", ({ params }) =>
    DETAILS[String(params.id)] ? HttpResponse.json(pageWords(Number(params.n))) : notFound(),
  ),
  http.post("/api/chat", async ({ request }) => {
    const body = (await request.json()) as { ipo_id: string; question: string; language: "en" | "hi" };
    if (!DETAILS[body.ipo_id]) return notFound();
    const steps = scenario(body.question, body.language);
    const enc = new TextEncoder();
    let i = 0;
    const stream = new ReadableStream<Uint8Array>({
      async pull(controller) {
        if (i >= steps.length) return controller.close();
        const { delay: ms, ev } = steps[i++];
        await new Promise((r) => setTimeout(r, ms * speed()));
        controller.enqueue(enc.encode("event: " + ev.event + "\ndata: " + JSON.stringify(ev.data) + "\n\n"));
      },
    });
    return new HttpResponse(stream, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" } });
  }),
  // Lab payloads: fixtures cut from the real eval_results files (mocks/lab.ts). No frontier file: the
  // Lab hides that section when the API has nothing, as it does on a machine without the E9 run.
  http.get("/api/lab/ladder", () => HttpResponse.json(LAB_LADDER)),
  http.get("/api/lab/verifier", () => HttpResponse.json(LAB_VERIFIER)),
  http.get("/api/lab/weaklabels", () => HttpResponse.json(LAB_WEAKLABELS)),
  http.get("/api/lab/retrieval", () => HttpResponse.json(LAB_RETRIEVAL)),
  http.get("/api/lab/asr", () => HttpResponse.json(LAB_ASR)),
  http.get("/api/lab/:name", () =>
    HttpResponse.json({ error: { code: "not_available", message: "No results yet." } }, { status: 404 }),
  ),
  http.post("/api/voice", async () => {
    await delay(900);
    return HttpResponse.json({
      transcript: "इस आईपीओ का पैसा कहाँ लगेगा?",
      language: "hi",
      asr_model: "mock",
      ms: 900,
    });
  }),
  http.get("/api/traces/:id", ({ params }) =>
    HttpResponse.json({
      trace_id: String(params.id),
      question: "(mock)",
      stages: [],
      passages: [],
      prompt:
        "You answer questions about an IPO offer document. Use only the passages below. Cite them as [n]. " +
        "If the passages do not contain the answer, say so.\n\n" +
        "[1] RHP p.120: Objects of the Offer. Capital expenditure (Rs. in million) 20,000.00 ...\n\n" +
        "Question: (mock)",
      checks: [],
      timings_ms: { guard: 3, retrieving: 410, generating: 5200, verifying: 40 },
    }),
  ),
];
