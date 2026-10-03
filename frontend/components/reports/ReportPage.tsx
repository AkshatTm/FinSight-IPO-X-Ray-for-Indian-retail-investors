"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
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
  const q = useQuery({
    queryKey: ["doc", docId],
    queryFn: () => apiGet<Schemas["DocDetail"]>(`/api/docs/${docId}`),
  });

  if (q.isPending) return <div aria-busy className="mx-auto mt-12 h-40 max-w-2xl animate-pulse rounded-[10px] bg-surface-2 motion-reduce:animate-none" />;
  if (q.isError) return <div className="mx-auto mt-12 max-w-2xl"><ErrorBlock error={q.error} onRetry={() => void q.refetch()} /></div>;

  const doc = q.data.doc;
  if (!showReport && (doc.status === "processing" || doc.status === "failed")) {
    return (
      <ProcessingScreen
        doc={doc}
        onSeeReady={() => {
          setShowReport(true);
          void qc.invalidateQueries({ queryKey: ["doc", docId] });
        }}
      />
    );
  }

  return <ReportView doc={doc} />;
}
