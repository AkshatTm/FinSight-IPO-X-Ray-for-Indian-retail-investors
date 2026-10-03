"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet, type Schemas } from "@/lib/api/client";

/** Upload limits from the API config (`uploads.*`); falls back to B01's defaults while loading. */
export function useLimits(): Schemas["UploadLimits"] & { loaded: boolean } {
  const q = useQuery({
    queryKey: ["upload-limits"],
    queryFn: () => apiGet<Schemas["UploadLimits"]>("/api/uploads/limits"),
    staleTime: 60_000,
  });
  const d = q.data ?? { enabled: true, max_mb: 50, max_pages: 1500, per_user_per_day: 3 };
  return { ...d, loaded: q.isSuccess };
}
