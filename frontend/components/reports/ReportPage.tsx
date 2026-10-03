"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
import { useT } from "@/lib/useT";
import { DocTypeBadge } from "./DocTypeBadge";
import { ProcessingScreen } from "./ProcessingScreen";

/**
 * /reports/[doc_id]: the processing screen while a job runs (B05 §4), then the report.
 * The report itself (B05 §5: Overview, Red flags, Risks, Compare, Ask) is built in B3.1; until
 * then the finished state shows the document header over skeleton sections.
 */
export function ReportPage({ docId }: { docId: string }) {
  const { t } = useT();
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

  return (
    <div className="mx-auto max-w-[1120px] py-10">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-[2rem] font-semibold leading-tight tracking-tight">{doc.company ?? t("proc.yourDoc")}</h1>
        {doc.doc_type && <DocTypeBadge type={doc.doc_type} />}
      </div>
      {doc.doc_type === "drhp" && <p className="mt-4 max-w-2xl rounded-[8px] border border-rule bg-surface-2 p-3 text-sm">{t("proc.drhp")}</p>}
      <div aria-busy className="mt-8 grid gap-4 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-36 rounded-[10px] border border-rule bg-surface p-4">
            {doc.status === "processing" && <p className="text-sm text-muted">{t("proc.stillWorking")}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
