"use client";

import Link from "next/link";
import { useEffect, useReducer, useState } from "react";
import type { Schemas } from "@/lib/api/client";
import type { StringKey } from "@/lib/i18n";
import { applyJobEvent, EMPTY_JOB, followJob, ROWS, rowState, type JobEvent, type JobView } from "@/lib/jobs";
import { rejectionFor } from "@/lib/upload";
import { useT } from "@/lib/useT";
import { DocTypeBadge } from "./DocTypeBadge";
import { StageRow } from "./StageRow";

const WARM_MS = 20_000;

function doneText(t: ReturnType<typeof useT>["t"], key: string, v: JobView): string {
  const d = (stage: string) => (v.stages[stage]?.detail ?? {}) as Record<string, unknown>;
  switch (key) {
    case "detected":
      return t("proc.detected.done", { pages: String(d("detected").pages ?? "") });
    case "parsed":
      return t("proc.parsed.done", { pages: String(d("parsed").pages_total ?? d("detected").pages ?? "") });
    case "sections":
      return t("proc.sections.done", { n: Array.isArray(d("sections").found) ? (d("sections").found as unknown[]).length : 0 });
    case "risks":
      return t("proc.risks.done", { n: String(d("risks_split").n_risks ?? "") });
    case "simplify": {
      const p = v.progress.simplify ?? { done: 0, total: 15 };
      return t("proc.simplify.done", { done: p.done, total: p.total });
    }
    default:
      return t(`proc.${key}.done` as StringKey);
  }
}

/** /reports/[doc_id] while processing (B05 §4): live stage list from the job's events. */
export function ProcessingScreen({ doc, onSeeReady }: { doc: Schemas["DocRecord"]; onSeeReady: () => void }) {
  const { t } = useT();
  const [view, dispatch] = useReducer((v: JobView, ev: JobEvent) => applyJobEvent(v, ev), EMPTY_JOB);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const ctrl = new AbortController();
    void (async () => {
      try {
        for await (const ev of followJob(doc.doc_id, ctrl.signal)) dispatch(ev);
      } catch {
        /* the stage list stays as it is; a reload resumes with the replay */
      }
    })();
    return () => ctrl.abort();
  }, [doc.doc_id]);

  const simplifyStart = view.stages.simplify?.startedAt ?? null;
  useEffect(() => {
    if (simplifyStart == null) return;
    const id = setInterval(() => setNow(Date.now()), 2000);
    return () => clearInterval(id);
  }, [simplifyStart]);

  const detected = view.stages.detected?.detail as { doc_type?: Schemas["DocRecord"]["doc_type"]; company?: string } | undefined;
  const type = detected?.doc_type ?? doc.doc_type ?? null;
  const company = detected?.company ?? doc.company ?? t("proc.yourDoc");
  const rejection = view.stages.validated?.status === "failed" ? rejectionFor(String(view.stages.validated.detail?.reason ?? "")) : null;
  const warming = simplifyStart != null && !view.progress.simplify && view.stages.simplify?.status === "running" && now - simplifyStart > WARM_MS;

  if (rejection) {
    return (
      <div className="mx-auto max-w-2xl py-12">
        <p role="alert" data-testid="rejection" className="rounded-[8px] border border-rule bg-surface-2 p-4">
          {t(`rej.${rejection}` as StringKey, { max_mb: 50 })}
        </p>
        <Link href="/upload" className="btn mt-6 inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-bg">
          {t("proc.tryAnother")}
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl py-12">
      <h1 className="text-[2rem] font-semibold leading-tight tracking-tight">{t("proc.title", { company })}</h1>
      <p className="mt-2 text-muted">{t("proc.sub")}</p>
      {type === "drhp" && <p className="mt-4 rounded-[8px] border border-rule bg-surface-2 p-3 text-sm">{t("proc.drhp")}</p>}
      {view.ready.includes("facts") && (
        <button type="button" onClick={onSeeReady} className="btn mt-6 inline-flex h-11 items-center rounded-[6px] bg-stamp px-5 font-medium text-bg">
          {t("proc.seeReady")}
        </button>
      )}
      <ol className="mt-6 divide-y divide-rule">
        {ROWS.map((row) => {
          const state = rowState(view, row.stages);
          const failed = row.stages.map((s) => view.stages[s]).find((i) => i?.status === "failed");
          const ms = row.stages.reduce<number | null>((acc, s) => (view.stages[s]?.ms != null ? (acc ?? 0) + (view.stages[s]?.ms ?? 0) : acc), null);
          return (
            <StageRow
              key={row.key}
              label={t(`proc.${row.key}` as StringKey)}
              state={state}
              doneText={state === "done" ? doneText(t, row.key, view) : null}
              ms={ms}
              reason={failed ? t(failed.detail?.skipped_because ? "proc.reason.skipped" : "proc.reason.error") : null}
              badge={row.key === "detected" && type ? <DocTypeBadge type={type} /> : undefined}
            />
          );
        })}
      </ol>
      {warming && <p role="status" className="mt-4 text-sm text-muted">{t("proc.warming")}</p>}
    </div>
  );
}
