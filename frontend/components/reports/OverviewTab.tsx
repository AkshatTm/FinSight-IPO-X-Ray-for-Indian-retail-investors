"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api/client";
import type { StringKey } from "@/lib/i18n";
import { anchorFor, categoryKey, flagTitleKey, offerLine, statusKey, type OfferLineParams, type ReportOverview, type RiskLevel, type RisksPage } from "@/lib/report";
import { useT } from "@/lib/useT";
import { RiskLevelCard } from "./RiskLevelCard";
import { StatusIcon } from "./StatusIcon";

/** Overview tab (B05 §5.3): risk level, five things to know, red flags at a glance, the offer. */
export function OverviewTab({ docId, report, onGo }: { docId: string; report: ReportOverview; onGo: (hash: string) => void }) {
  const { t } = useT();
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
  const offer = offerLine(report.offer_line_params as OfferLineParams | null);
  const flags = (report.redflags_summary ?? []) as { id: string; status: Parameters<typeof statusKey>[0] }[];

  return (
    <div className="space-y-8">
      {level.data ? <RiskLevelCard level={level.data} onReason={onGo} /> : <NotReady />}

      <section aria-labelledby="ov-five">
        <h2 id="ov-five" className="text-lg font-semibold">{t("ov.five")}</h2>
        {top.data && top.data.risks.length > 0 ? (
          <ol className="mt-3 space-y-3">
            {top.data.risks.slice(0, 5).map((r) => {
              const cat = categoryKey(r.category);
              return (
                <li key={r.rid} className="rounded-[10px] border border-rule bg-surface p-4">
                  <p className="text-sm">{r.simple_status === "ready" && r.simple ? r.simple : r.title}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    {cat && <span className="rounded-full bg-surface-2 px-2 py-0.5">{t(cat)}</span>}
                    <button type="button" className="underline underline-offset-2" onClick={() => onGo(`#${anchorFor("risk", r.rid)}`)}>
                      {t("ov.readMore")}
                    </button>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : (
          <NotReady />
        )}
      </section>

      <section aria-labelledby="ov-flags">
        <h2 id="ov-flags" className="text-lg font-semibold">{t("ov.flags")}</h2>
        {flags.length > 0 ? (
          <ul className="mt-3 flex flex-wrap gap-2">
            {flags.map((f) => (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => onGo(`#${anchorFor("redflag", f.id)}`)}
                  className="inline-flex items-center gap-1.5 rounded-full border border-rule px-3 py-1 text-xs hover:bg-surface-2"
                >
                  <StatusIcon status={f.status} size={14} />
                  <span>{flagTitleKey(f.id) ? t(flagTitleKey(f.id) as StringKey) : f.id}</span>
                  <span className="text-muted">{t(statusKey(f.status))}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <NotReady />
        )}
      </section>

      {offer && (
        <section aria-labelledby="ov-offer">
          <h2 id="ov-offer" className="text-lg font-semibold">{t("ov.offerTitle")}</h2>
          <p className="mt-2">{t(offer.key as StringKey, offer.vars)}</p>
        </section>
      )}

      <p className="text-xs text-muted">{t("ov.footer")}</p>
    </div>
  );
}

export function NotReady() {
  const { t } = useT();
  return <p className="mt-2 text-sm text-muted">{t("rep.notReady")}</p>;
}
