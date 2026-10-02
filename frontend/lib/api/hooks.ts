"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet, type Schemas } from "./client";

export const useIpos = () =>
  useQuery({ queryKey: ["ipos"], queryFn: () => apiGet<Schemas["IpoSummary"][]>("/api/ipos") });

export const useIpo = (id: string) =>
  useQuery({ queryKey: ["ipo", id], queryFn: () => apiGet<Schemas["IpoDetail"]>(`/api/ipos/${id}`) });

export const useXray = (id: string, enabled = true) =>
  useQuery({
    queryKey: ["xray", id],
    queryFn: () => apiGet<Schemas["XRayResponse"]>(`/api/ipos/${id}/xray`),
    enabled,
  });

export const useSuggested = (id: string) =>
  useQuery({
    queryKey: ["suggested", id],
    queryFn: () => apiGet<Schemas["SuggestedQuestion"][]>(`/api/ipos/${id}/suggested-questions`),
  });

export const useWords = (ipoId: string, doc: string, page: number, enabled = true) =>
  useQuery({
    queryKey: ["words", ipoId, doc, page],
    queryFn: () => apiGet<Schemas["PageWords"]>(`/api/ipos/${ipoId}/pages/${page}/words?doc=${doc}`),
    enabled,
    staleTime: Infinity,
  });

export const useTrace = (traceId: string | undefined, enabled: boolean) =>
  useQuery({
    queryKey: ["trace", traceId],
    queryFn: () => apiGet<Schemas["Trace"]>(`/api/traces/${traceId}`),
    enabled: enabled && !!traceId,
    staleTime: Infinity,
  });

/** Model Lab payloads are free-form JSON (spec 8); callers read what they need defensively. */
export const useLab = (name: "ladder" | "fields" | "verifier" | "weaklabels" | "frontier" | "retrieval" | "asr") =>
  useQuery({
    queryKey: ["lab", name],
    queryFn: () => apiGet<Record<string, unknown>>(`/api/lab/${name}`),
    retry: false,
    staleTime: Infinity,
  });
