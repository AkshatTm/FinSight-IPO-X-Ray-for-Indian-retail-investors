"use client";

import { UnitToggle } from "@/components/workspace/UnitToggle";
import type { StringKey } from "@/lib/copy";
import type { Unit } from "@/lib/format";
import { useUi } from "@/lib/store";
import { byPeriod, cell, FY_ORDER, fyLabels, hasFinancials, issuerPeer, ratioText, type Sod, type SodRatio } from "@/lib/sod";
import { formatPercent } from "@/lib/format";
import type { ReportOverview } from "@/lib/report";
import { parseSod } from "@/lib/sod";
import { useT } from "@/lib/useT";
import { SectionTitle } from "./OverviewParts";
import { FinChart } from "./ReportCharts";

// Row order and kind. Per-share rows are in rupees and ignore the unit toggle.
const ROWS: { key: string; perShare?: boolean }[] = [
  { key: "revenue" },
  { key: "total_income" },
  { key: "profit_after_tax" },
  { key: "operating_cash_flow" },
  { key: "net_worth" },
  { key: "total_borrowings" },
  { key: "equity_share_capital" },
  { key: "eps_basic", perShare: true },
  { key: "eps_diluted", perShare: true },
  { key: "nav_per_share", perShare: true },
];

export function FinancialsTab({ report }: { report: ReportOverview }) {
  const { t } = useT();
  const unit = useUi((s) => s.unit);
  const sod = parseSod(report.sod);
  if (!hasFinancials(sod)) {
    return (
      <section aria-labelledby="fin-title" className="max-w-[62ch]">
        <SectionTitle id="fin-title">{t("fin.title")}</SectionTitle>
        <p className="mt-3 text-muted">{t("fin.empty")}</p>
      </section>
    );
  }
  return (
    <section aria-labelledby="fin-title" className="space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <SectionTitle id="fin-title">{t("fin.title")}</SectionTitle>
          <p className="mt-1 text-sm text-muted">{t("fin.sub", { unit: t(`unit.${unit}`) })}</p>
          {!sod.has_sod && <p className="mt-1 max-w-[62ch] text-sm text-muted">{t("fin.noSod")}</p>}
        </div>
        <UnitToggle />
      </header>
      <FinChart sod={sod} unit={unit} />
      <FinTable sod={sod} unit={unit} />
      <Ratios sod={sod} facts={report.facts_summary} unit={unit} />
    </section>
  );
}

function FinTable({ sod, unit }: { sod: Sod; unit: Unit }) {
  const { t } = useT();
  const labels = fyLabels(sod);
  const rows = ROWS.filter((r) => sod.financials[r.key]);
  const stubPeriod = rows.map((r) => byPeriod(sod.financials[r.key]).stub?.period ?? "").find((p) => p && p !== "stub") ?? null;
  const hasStub = rows.some((r) => byPeriod(sod.financials[r.key]).stub);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[620px] text-sm">
        <thead>
          <tr className="border-b border-rule text-right text-muted">
            <th scope="col" className="py-2 pr-4 text-left font-normal">
              <span className="sr-only">Item</span>
            </th>
            {FY_ORDER.map((p) => (
              <th key={p} scope="col" className="px-3 py-2 font-medium text-text">{labels[p]}</th>
            ))}
            {hasStub && (
              <th scope="col" className="px-3 py-2 font-medium text-text">
                {t("fin.stub")}
                {stubPeriod && <span className="block max-w-[14rem] text-xs font-normal text-muted">{stubPeriod}</span>}
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {rows.map((r) => {
            const { fy, stub } = byPeriod(sod.financials[r.key]);
            const cells = [...FY_ORDER.map((p) => cell(fy[p] ?? null, unit, r.perShare)), ...(hasStub ? [cell(stub, unit, r.perShare)] : [])];
            return (
              <tr key={r.key}>
                <th scope="row" className="py-2.5 pr-4 text-left font-normal">{t(`fin.row.${r.key}` as StringKey)}</th>
                {cells.map((c, i) => (
                  <td key={i} className="num px-3 py-2.5 text-right">
                    {c.text ?? <span className="text-muted">{t("fin.notStated")}</span>}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Ratios({ sod, facts, unit }: { sod: Sod; facts: unknown; unit: Unit }) {
  const { t } = useT();
  const issuer = issuerPeer(facts);
  const items: { key: string; label: string; value: string | null; note?: string; formula?: string | null; page?: number | null }[] = sod.derived.map((r: SodRatio) => ({
    key: `${r.key}-${r.period}`,
    label: t(`fin.ratio.${r.key}` as StringKey),
    value: ratioText(r, unit),
    note: r.status === "not_available" ? (r.reason ?? undefined) : undefined,
    formula: r.formula,
    page: r.pages[0] ?? null,
  }));
  if (issuer?.ronw != null && Number.isFinite(Number(issuer.ronw))) {
    items.push({ key: "ronw", label: t("fin.ratio.ronw"), value: formatPercent(Number(issuer.ronw)), page: issuer.page });
  }
  if (issuer) {
    const pe = issuer.pe != null && Number.isFinite(Number(issuer.pe)) ? `${Number(issuer.pe).toFixed(1)}×` : null;
    items.push({ key: "pe", label: t("fin.ratio.pe"), value: pe, note: pe ? undefined : t("fin.peNote"), page: issuer.page });
  }
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="fin-ratios">
      <SectionTitle id="fin-ratios">{t("fin.ratios")}</SectionTitle>
      <dl className="mt-3 divide-y divide-rule border-y border-rule">
        {items.map((i) => (
          <div key={i.key} className="py-2.5">
            <div className="flex items-baseline justify-between gap-4">
              <dt>{i.label}</dt>
              <dd className="num font-medium">{i.value ?? <span className="font-normal text-muted">{i.note ?? t("fin.notStated")}</span>}</dd>
            </div>
            {i.formula && i.value && (
              <p className="mt-0.5 text-xs text-muted">
                {i.formula}
                {i.page ? ` · ${t("fin.source", { p: i.page })}` : ""}
              </p>
            )}
          </div>
        ))}
      </dl>
    </section>
  );
}
