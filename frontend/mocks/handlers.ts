import { http, HttpResponse, delay } from "msw";
import { DETAILS, HEALTH, IPOS } from "./fixtures";
import { buildXray, SUGGESTED } from "./xray";

const notFound = () =>
  HttpResponse.json(
    { error: { code: "ipo_not_found", message: "IPO not found" } },
    { status: 404 },
  );

export const handlers = [
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
];
