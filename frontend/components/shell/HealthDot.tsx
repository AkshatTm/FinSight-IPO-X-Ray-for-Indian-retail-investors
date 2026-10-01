"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet, ApiError, type Schemas } from "@/lib/api/client";
import { useT } from "@/lib/useT";

export type HealthState = "ok" | "warming" | "degraded" | "unreachable";

export function useHealth(): { state: HealthState; detail: string } {
  const { data, error } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<Schemas["HealthResponse"]>("/api/health"),
    refetchInterval: (q) => (q.state.data?.status === "ok" ? 30_000 : 5_000),
    retry: 0,
  });
  if (error instanceof ApiError || (error && !data)) return { state: "unreachable", detail: "" };
  if (!data) return { state: "warming", detail: "" };
  const detail = Object.entries(data.models)
    .filter(([, m]) => !m.loaded && !m.lazy)
    .map(([k]) => k)
    .join(", ");
  return { state: data.status, detail };
}

/** Uses the stamp colour, never the verdict colours (spec 3.2). */
export function HealthDot() {
  const { t } = useT();
  const { state, detail } = useHealth();
  const label = t(`health.${state}`, { detail });
  const fill =
    state === "ok"
      ? "bg-stamp border-muted"
      : state === "warming"
        ? "bg-stamp/50 border-muted animate-pulse"
        : state === "degraded"
          ? "bg-transparent border-stamp"
          : "bg-transparent border-muted";
  return (
    <span
      role="img"
      aria-label={`${t("health.label")}: ${label}`}
      title={label}
      className="inline-flex h-11 w-8 items-center justify-center"
    >
      <span className={`block h-2.5 w-2.5 rounded-full border ${fill}`} />
    </span>
  );
}
