import { http, HttpResponse, delay } from "msw";
import { DETAILS, HEALTH, IPOS } from "./fixtures";
import { pageSvg } from "./pages";
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
];
