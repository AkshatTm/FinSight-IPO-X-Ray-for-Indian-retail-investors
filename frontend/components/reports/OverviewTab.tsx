"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api/client";
import { anchorFor, categoryKey, type ReportOverview, type RiskLevel, type RisksPage } from "@/lib/report";
import { parseSod } from "@/lib/sod";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { FlagsGlance, KeyFacts, PromoterHolding, SectionTitle, Strengths } from "./OverviewParts";
import { RiskLevelCard } from "./RiskLevelCard";

/** Overview: key facts and promoter holding on the left; the risk level with its reasons beside them. */
export function OverviewTab({ docId, report, onGo }: { docId: string; report: ReportOverview; onGo: (hash: string) => void }) {
  const { t } = useT();
  const unit = useUi((s) => s.unit);
  const sod = parseSod(report.sod);
  const level = useQuery({
    queryKey: ["risk-level", docId],
    queryFn: () => apiGet<RiskLevel>(`/api/docs/${docId}/risk-level`),
    retry: false,
  });
  // Live list, so rewrites that landed after report.json was written are shown.
  const top = useQuery({
    queryKey: ["risks", docId, "importance", "", "", false],
    queryFn: () => apiGet<RisksPage>(`/api/docs/${docId}/risks?sort=importance`),
    retry: false,
  });
  const flags = (report.redflags_summary ?? []) as { id: string; status: Parameters<typeof FlagsGlance>[0]["flags"][number]["status"] }[];

  return (
    <div className="grid gap-x-12 gap-y-10 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-10 lg:col-start-1 lg:row-start-1">
        <KeyFacts report={report} sod={sod} unit={unit} />
        <PromoterHolding sod={sod} />

        <section aria-labelledby="ov-five">
          <SectionTitle id="ov-five">{t("ov.five")}</SectionTitle>
          {top.data && top.data.risks.length > 0 ? (
            <ol className="mt-3 divide-y divide-rule border-y border-rule">
              {top.data.risks.slice(0, 5).map((r) => {
                const cat = categoryKey(r.category);
                return (
                  <li key={r.rid} className="py-3">
                    <p className="max-w-[68ch]">{r.simple_status === "ready" && r.simple ? r.simple : r.title}</p>
                    <p className="mt-1.5 flex flex-wrap items-center gap-x-3 text-xs text-muted">
                      {cat && <span>{t(cat)}</span>}
                      <button type="button" className="text-stamp underline underline-offset-4" onClick={() => onGo(`#${anchorFor("risk", r.rid)}`)}>
                        {t("ov.readMore")}
                      </button>
                    </p>
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className="mt-3 text-sm text-muted">{t("rep.notReady")}</p>
          )}
        </section>

        <section aria-labelledby="ov-flags">
          <SectionTitle id="ov-flags">{t("ov.flags")}</SectionTitle>
          <FlagsGlance flags={flags} onGo={onGo} />
        </section>

        <Strengths sod={sod} />
        <p className="text-xs text-muted">{t("ov.footer")}</p>
      </div>

      <aside className="order-first lg:order-none lg:col-start-2 lg:row-start-1">
        <div className="lg:sticky lg:top-40">
          {level.data ? <RiskLevelCard level={level.data} onReason={onGo} /> : <NotReady text={level.isError ? t("ov.noRiskLevel") : null} />}
        </div>
      </aside>
    </div>
  );
}

export function NotReady({ text }: { text?: string | null }) {
  const { t } = useT();
  return <p className="text-sm text-muted">{text ?? t("rep.notReady")}</p>;
}
