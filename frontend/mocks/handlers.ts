import { http, HttpResponse, delay } from "msw";
import { DETAILS, HEALTH, IPOS } from "./fixtures";

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
];
