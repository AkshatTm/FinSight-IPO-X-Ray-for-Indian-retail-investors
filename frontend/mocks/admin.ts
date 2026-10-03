import { http, HttpResponse } from "msw";
import type { Schemas } from "@/lib/api/client";

// Admin mocks (B3.5a): synthetic numbers shaped like GET /api/admin/costs and /api/admin/jobs.
// The mock user is the admin, as with auth mode "off" on a laptop.

export const ADMIN_COSTS: Schemas["CostSummary"] = {
  days: [
    { date: "2026-10-02", uploads: 2, jobs: 2, failed: 1, vcpu_s: 2280, gib_s: 4560, gpu_s: 0, usd: 0.05 },
    { date: "2026-10-03", uploads: 3, jobs: 3, failed: 0, vcpu_s: 3420, gib_s: 6840, gpu_s: 0, usd: 0.08 },
  ],
  total: { uploads: 5, jobs: 5, vcpu_s: 5700, gib_s: 11400, usd: 0.13, free_vcpu_share: 0.02375, free_gib_share: 0.025333 },
  usd_incomplete: false,
  provisional: true,
  window_days: 31,
};

export const ADMIN_FAILED: Schemas["FailedJob"][] = [
  {
    job: {
      job_id: "job_mock_failed_1",
      doc_id: "doc_00000000000000aa",
      stage: "validated",
      status: "failed",
      error: "scanned",
      started_at: "2026-10-02T05:10:00Z",
      finished_at: "2026-10-02T05:10:04Z",
    },
    created_at: "2026-10-02T05:09:58Z",
    company: null,
  },
];

export const adminHandlers = [
  http.get("/api/admin/costs", () => HttpResponse.json(ADMIN_COSTS)),
  http.get("/api/admin/jobs", () => HttpResponse.json(ADMIN_FAILED)),
];
