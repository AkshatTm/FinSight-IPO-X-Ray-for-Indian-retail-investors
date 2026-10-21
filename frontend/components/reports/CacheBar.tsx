"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, apiSend, type Schemas } from "@/lib/api/client";
import type { StringKey } from "@/lib/i18n";
import { useToast } from "@/lib/toast";
import { useT } from "@/lib/useT";

const MODELS = ["ollama", "classifier", "embeddings", "reranker"] as const;
type Confirm = "delete" | "reanalyse" | null;

/** "skipped_model:ollama" → "analysed without the plain-English writer"; other reasons as stored. */
export function reasonText(t: ReturnType<typeof useT>["t"], reason: string): string {
  const [kind, what = ""] = reason.split(":");
  if (kind === "skipped_model") return t("cache.reason.skipped", { model: t(`cache.model.${what}` as StringKey) });
  if (kind === "stage_failed" || kind === "failed") return t("cache.reason.stage", { stage: what });
  if (kind === "model_missing") return t("cache.reason.missing", { model: t(`cache.model.${what}` as StringKey) });
  return reason;
}

/**
 * Cache v2 (CC-04) above a report: the re-analysing and degraded banners, why a stale analysis was
 * kept, and the Re-analyse and Delete buttons (each behind a confirmation).
 */
export function CacheBar({
  doc,
  cache,
  reanalysing,
  onRestarted,
}: {
  doc: Schemas["DocRecord"];
  cache?: Schemas["CacheInfo"] | null;
  reanalysing: boolean;
  onRestarted: () => void;
}) {
  const { t } = useT();
  const qc = useQueryClient();
  const router = useRouter();
  const toast = useToast((s) => s.show);
  const [confirm, setConfirm] = useState<Confirm>(null);
  const [refused, setRefused] = useState<string | null>(null);

  const restart = useMutation({
    mutationFn: (without: boolean) =>
      apiSend<Schemas["JobStarted"]>("POST", `/api/docs/${doc.doc_id}/reanalyse`, { analyse_without: without ? MODELS : [] }),
    onSuccess: () => {
      setConfirm(null);
      setRefused(null);
      onRestarted();
      void qc.invalidateQueries({ predicate: (q) => q.queryKey.includes(doc.doc_id) });
    },
    onError: (e) => {
      setConfirm(null);
      setRefused(e instanceof ApiError && e.code === "models_unavailable" ? e.message : t("err.internal_error"));
    },
  });
  const remove = useMutation({
    mutationFn: () => apiSend<{ deleted: string }>("DELETE", `/api/docs/${doc.doc_id}`),
    onSuccess: () => {
      toast(t("cache.deleted"));
      qc.removeQueries({ predicate: (q) => q.queryKey.includes(doc.doc_id) });
      router.push("/upload");
    },
    onError: () => {
      setConfirm(null);
      setRefused(t("err.internal_error"));
    },
  });

  const busy = doc.status === "processing";
  const reasons = (doc.analysis_status === "degraded" || doc.analysis_status === "failed" ? doc.degraded_reasons : []) ?? [];
  const box = "mt-4 rounded-[8px] border border-rule bg-surface-2 p-3 text-sm";
  const button = "rounded-full border border-rule px-3 py-0.5 text-sm text-text hover:bg-surface-2 disabled:opacity-50";

  return (
    <div className="mx-auto max-w-[1120px]" data-testid="cache-bar">
      {(reanalysing || cache?.reanalysing) && (
        <p role="status" className={box}>
          {t("cache.reanalysing")}
        </p>
      )}
      {!busy && doc.analysis_status === "degraded" && (
        <p role="alert" data-testid="degraded-banner" className={box}>
          <strong>{t("cache.degraded")}</strong> {reasons.map((r) => reasonText(t, r)).join("; ")}
        </p>
      )}
      {!busy && doc.analysis_status === "failed" && doc.rejection == null && (
        <p role="alert" className={box}>
          <strong>{t("cache.failed")}</strong> {reasons.map((r) => reasonText(t, r)).join("; ")}
        </p>
      )}
      {cache?.blocked && !refused && <p className={box}>{t("cache.blocked", { why: cache.blocked })}</p>}
      {refused && (
        <div role="alert" data-testid="refused" className={box}>
          <p>{refused}</p>
          <button type="button" className={`${button} mt-2`} onClick={() => restart.mutate(true)} disabled={restart.isPending}>
            {t("cache.without")}
          </button>
        </div>
      )}

      {!busy && doc.rejection == null && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button type="button" className={button} onClick={() => setConfirm("reanalyse")}>
            {t("cache.reanalyse")}
          </button>
          <button type="button" className={button} onClick={() => setConfirm("delete")}>
            {t("cache.delete")}
          </button>
        </div>
      )}

      {confirm && (
        <div role="alertdialog" aria-labelledby="cache-confirm-title" data-testid="confirm" className="mt-3 max-w-xl rounded-[8px] border border-rule bg-surface p-4">
          <h2 id="cache-confirm-title" className="font-semibold">
            {t(confirm === "delete" ? "cache.confirmDelete.title" : "cache.confirmRe.title")}
          </h2>
          <p className="mt-1 text-sm text-muted">{t(confirm === "delete" ? "cache.confirmDelete.body" : "cache.confirmRe.body")}</p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              className="rounded-[6px] bg-stamp px-4 py-1.5 text-sm font-medium text-bg disabled:opacity-50"
              disabled={restart.isPending || remove.isPending}
              onClick={() => (confirm === "delete" ? remove.mutate() : restart.mutate(false))}
            >
              {t(confirm === "delete" ? "cache.confirmDelete.go" : "cache.confirmRe.go")}
            </button>
            <button type="button" className={button} onClick={() => setConfirm(null)}>
              {t("cache.cancel")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
