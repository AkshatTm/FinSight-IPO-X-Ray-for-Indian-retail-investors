"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { tabForHash, TABS, type ReportOverview, type Tab } from "@/lib/report";
import { useT } from "@/lib/useT";
import { CompareTab } from "./CompareTab";
import { DocTypeBadge } from "./DocTypeBadge";
import { OverviewTab } from "./OverviewTab";
import { RedFlagsTab } from "./RedFlagsTab";
import { RisksTab } from "./RisksTab";

/**
 * The finished report (B05 §5): sticky header and the tabs Overview · Red flags · Risks · Compare.
 * A hash such as "#redflag-RF03" or "#risk-r12" opens its tab and scrolls to the card. Facts and
 * Document stay on the showcase pages until uploads have them (B06 aliases).
 */
export function ReportView({ doc }: { doc: Schemas["DocRecord"] }) {
  const { t, lang } = useT();
  // Mounted on the client only (after the document query), so the hash can seed the state.
  const [tab, setTab] = useState<Tab>(() => tabForHash(window.location.hash) ?? "overview");
  const [focus, setFocus] = useState<string | null>(() => window.location.hash || null);
  const [copied, setCopied] = useState(false);
  const report = useQuery({
    queryKey: ["report", doc.doc_id],
    queryFn: () => apiGet<ReportOverview>(`/api/docs/${doc.doc_id}/report`),
  });

  const go = useCallback((hash: string) => {
    const next = tabForHash(hash);
    if (next) setTab(next);
    setFocus(hash.startsWith("#") ? hash : `#${hash}`);
    window.history.replaceState(null, "", hash.startsWith("#") ? hash : `#${hash}`);
  }, []);

  useEffect(() => {
    if (!focus || tab === "risks") return; // the Risks tab scrolls itself once its list has loaded
    const id = setTimeout(() => document.getElementById(focus.replace(/^#/, ""))?.scrollIntoView({ block: "start" }), 300);
    return () => clearTimeout(id);
  }, [focus, tab]);

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href.split("#")[0]);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1120px] py-8">
      <header className="sticky top-0 z-20 -mx-4 border-b border-rule bg-bg/95 px-4 pb-3 pt-2 backdrop-blur">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[2rem] font-semibold leading-tight tracking-tight">{doc.company ?? t("proc.yourDoc")}</h1>
          {doc.doc_type && <DocTypeBadge type={doc.doc_type} />}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          {doc.pages && <span>{t("rep.pages", { n: doc.pages })}</span>}
          <span>{t("rep.analysed", { date: formatDate(doc.created_at, lang) })}</span>
          <button type="button" onClick={() => void share()} className="rounded-full border border-rule px-3 py-0.5 text-text hover:bg-surface-2">
            {copied ? t("rep.copied") : t("rep.share")}
          </button>
          {report.data?.companion_doc_id && (
            <Link href={`/reports/${report.data.companion_doc_id}`} className="underline underline-offset-2">
              {t("rep.companion")}
            </Link>
          )}
        </div>
        <nav role="tablist" aria-label={doc.company ?? "report"} className="-mb-3 mt-3 flex gap-1 overflow-x-auto">
          {TABS.map((id) => (
            <button
              key={id}
              type="button"
              role="tab"
              id={`tab-${id}`}
              aria-selected={tab === id}
              aria-controls={`panel-${id}`}
              onClick={() => {
                setTab(id);
                setFocus(null);
              }}
              className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm ${tab === id ? "border-stamp font-semibold" : "border-transparent text-muted hover:text-text"}`}
            >
              {t(`tab.${id}`)}
            </button>
          ))}
        </nav>
      </header>
      {doc.doc_type === "drhp" && <p className="mt-4 max-w-2xl rounded-[8px] border border-rule bg-surface-2 p-3 text-sm">{t("proc.drhp")}</p>}
      {lang === "hi" && tab !== "compare" && <p className="mt-4 rounded-[8px] border border-rule bg-surface-2 p-3 text-sm">{t("rep.englishOnly")}</p>}

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="mt-6">
        {report.isError && <ErrorBlock error={report.error} onRetry={() => void report.refetch()} />}
        {tab === "overview" && report.data && <OverviewTab docId={doc.doc_id} report={report.data} onGo={go} />}
        {tab === "redflags" && <RedFlagsTab docId={doc.doc_id} />}
        {tab === "risks" && <RisksTab docId={doc.doc_id} focus={focus} />}
        {tab === "compare" && <CompareTab docId={doc.doc_id} />}
      </div>
    </div>
  );
}
