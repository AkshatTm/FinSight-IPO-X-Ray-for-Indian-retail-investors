"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
import { CacheBar } from "./CacheBar";
import { ProcessingScreen } from "./ProcessingScreen";
import { ReportView } from "./ReportView";

/**
 * /reports/[doc_id]: the processing screen while a job runs (B05 §4), then the report.
 * The report itself (B05 §5) is `ReportView`; parts that are not ready show their own
 * "not ready" line, so a partial report still opens.
 */
export function ReportPage({ docId }: { docId: string }) {
  const qc = useQueryClient();
  const [showReport, setShowReport] = useState(false);
  const [reanalysing, setReanalysing] = useState(false);
  const q = useQuery({
    queryKey: ["doc", docId],
    queryFn: () => apiGet<Schemas["DocDetail"]>(`/api/docs/${docId}`),
    refetchInterval: (query) => (query.state.data?.doc.status === "processing" ? 5000 : false),
  });

  // A report opened early ("See what's ready") fills in as the job finishes its steps: refresh
  // every part of this document while the job runs, and once more when it ends.
  const processing = q.data?.doc.status === "processing";
  const wasProcessing = useRef(false);
  useEffect(() => {
    const refresh = () =>
      void qc.invalidateQueries({ predicate: (x) => x.queryKey.includes(docId) && x.queryKey[0] !== "doc" });
    if (processing) {
      wasProcessing.current = true;
      const id = setInterval(refresh, 6000);
      return () => clearInterval(id);
    }
    if (wasProcessing.current) {
      wasProcessing.current = false;
      refresh();
    }
  }, [processing, docId, qc]);

  if (q.isPending) return <div aria-busy className="mx-auto mt-12 h-40 max-w-2xl animate-pulse rounded-[10px] bg-surface-2 motion-reduce:animate-none" />;
  if (q.isError) return <div className="mx-auto mt-12 max-w-2xl"><ErrorBlock error={q.error} onRetry={() => void q.refetch()} /></div>;

  const doc = q.data.doc;
  const stale = reanalysing || !!q.data.cache?.reanalysing;
  const bar = (
    <CacheBar
      doc={doc}
      cache={q.data.cache}
      reanalysing={stale && doc.status === "processing"}
      onRestarted={() => {
        setShowReport(false);
        setReanalysing(true);
      }}
    />
  );
  if (!showReport && (doc.status === "processing" || doc.status === "failed")) {
    return (
      <>
        {bar}
        <ProcessingScreen
          key={q.data.job_id ?? "none"}
          doc={doc}
          onSeeReady={() => {
            setShowReport(true);
            void qc.invalidateQueries({ queryKey: ["doc", docId] });
          }}
        />
      </>
    );
  }

  const workspaceReady = q.data.stages.some((s) => s.stage === "index" && s.status === "done");
  return (
    <>
      {bar}
      <ReportView doc={doc} workspaceReady={workspaceReady} />
    </>
  );
}
