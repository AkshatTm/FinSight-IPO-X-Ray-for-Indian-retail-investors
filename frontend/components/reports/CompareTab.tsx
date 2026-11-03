"use client";

import { useQuery } from "@tanstack/react-query";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet } from "@/lib/api/client";
import { metricValue, orderPeers, peerCell, roundPercentile, sourcePage, type CompareData, type Metric, type Peer } from "@/lib/compare";
import type { StringKey } from "@/lib/copy";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";

const COLUMNS = [
  { kind: "pe", label: "cmp.colPe", tip: "cmp.tipPe" },
  { kind: "eps", label: "cmp.colEps", tip: null },
  { kind: "ronw", label: "cmp.colRonw", tip: "cmp.tipRonw" },
  { kind: "nav", label: "cmp.colNav", tip: null },
] as const;

/** Compare tab (B05 §5.6): listed peers from the document, then percentile bars against past IPOs. */
export function CompareTab({ docId }: { docId: string }) {
  const q = useQuery({
    queryKey: ["compare", docId],
    queryFn: () => apiGet<CompareData>(`/api/docs/${docId}/compare`),
  });
  if (q.isPending) return <div aria-busy className="h-48 animate-pulse rounded-[10px] bg-surface-2 motion-reduce:animate-none" />;
  if (q.isError) return <ErrorBlock error={q.error} onRetry={() => void q.refetch()} />;
  return <CompareView data={q.data} />;
}

/** The fixed fields every report shows for this IPO, with "Not stated" where the document leaves them out. */
function FixedFields({ issuer }: { issuer: Peer | null }) {
  const { t } = useT();
  return (
    <dl className="mt-4 max-w-md divide-y divide-rule border-y border-rule">
      {COLUMNS.map((c) => {
        const v = issuer ? peerCell(issuer[c.kind], c.kind) : "—";
        return (
          <div key={c.kind} className="flex items-baseline justify-between gap-4 py-2.5">
            <dt className="text-muted">{t(c.label)}</dt>
            <dd className="num font-medium">{v === "—" ? <span className="font-normal text-muted">{t("cmp.notStated")}</span> : v}</dd>
          </div>
        );
      })}
    </dl>
  );
}

export function CompareView({ data }: { data: CompareData }) {
  const { t } = useT();
  const unit = useUi((s) => s.unit);
  const peers = orderPeers(data.peers ?? []);
  const bars = data.percentiles ?? [];
  const page = sourcePage(peers);
  const corpusN = bars[0]?.corpus_n ?? 0;
  return (
    <section aria-labelledby="cmp-title" className="space-y-8">
      <header>
        <h2 id="cmp-title" className="font-serif text-xl font-semibold tracking-tight">{t("cmp.title")}</h2>
        {corpusN > 0 && <p className="mt-1 text-sm text-muted">{t("cmp.sub", { n: corpusN })}</p>}
        {data.provisional && <p className="mt-1 text-sm text-muted">{t("cmp.provisional")}</p>}
      </header>

      {peers.length === 0 ? (
        <div>
          <p className="text-sm text-muted">{t("cmp.noPeers")}</p>
          <FixedFields issuer={null} />
        </div>
      ) : (
        <div>
          <div className="overflow-x-auto border-y border-rule">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="text-left text-muted">
                <tr>
                  <th scope="col" className="p-3 font-normal">{t("cmp.colCompany")}</th>
                  {COLUMNS.map((c) => (
                    <th key={c.kind} scope="col" className="p-3 text-right font-normal" title={c.tip ? t(c.tip) : undefined}>
                      {t(c.label)}
                      {c.tip && <span className="sr-only">: {t(c.tip)}</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {peers.map((p) => (
                  <tr key={p.name} className={p.is_issuer ? "bg-stamp/10 font-medium" : "border-t border-rule"}>
                    <th scope="row" className="p-3 text-left font-normal">
                      {p.name}
                      {p.is_issuer && <span className="ml-2 rounded-[4px] bg-stamp/20 px-1.5 py-0.5 text-xs">{t("cmp.issuer")}</span>}
                    </th>
                    {COLUMNS.map((c) => (
                      <td key={c.kind} className="p-3 text-right tabular-nums">{peerCell(p[c.kind], c.kind)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {page !== null && <p className="mt-2 text-xs text-muted">{t("cmp.source", { p: page })}</p>}
        </div>
      )}

      <div>
        <h3 className="text-base font-semibold">{t("cmp.pastTitle")}</h3>
        {bars.length === 0 ? (
          <p className="mt-2 text-sm text-muted">{t("cmp.noData")}</p>
        ) : (
          <ul className="mt-3 space-y-4">
            {bars.map((b) => {
              const p = roundPercentile(b.percentile);
              return (
                <li key={b.metric}>
                  <div className="flex items-baseline justify-between gap-4 text-sm">
                    <span className="font-medium">{t(`cmp.metric.${b.metric}` as StringKey)}</span>
                    <span className="tabular-nums">{metricValue(b.metric as Metric, b.value, unit)}</span>
                  </div>
                  <div className="mt-1 h-2 rounded-[2px] bg-surface-2" role="img" aria-label={t("cmp.higherThan", { p })}>
                    <div className="h-2 rounded-[2px] bg-stamp" style={{ width: `${p}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-muted">{t("cmp.higherThan", { p })}</p>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
