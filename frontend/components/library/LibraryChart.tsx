"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Ipo } from "@/lib/library";
import { useT } from "@/lib/useT";

const CR = 1e7;

/** Issue size of every IPO, split into fresh issue (saffron) and offer for sale (sand). Hidden with fewer than two sizes. */
export function LibraryChart({ ipos }: { ipos: Ipo[] }) {
  const { t } = useT();
  const rows = ipos
    .filter((i) => i.issue_size_inr && Number.isFinite(Number(i.issue_size_inr)))
    .map((i) => ({
      name: i.company.replace(/ (Limited|Ltd\.?)$/i, ""),
      fresh: Number(i.fresh_inr ?? 0) / CR,
      ofs: Number(i.ofs_inr ?? 0) / CR,
      total: Number(i.issue_size_inr) / CR,
    }))
    .sort((a, b) => b.total - a.total);
  if (rows.length < 2) return null;
  return (
    <section aria-labelledby="lib-chart" className="mb-8 rounded-[16px] border border-rule bg-surface p-5 shadow-[var(--shadow-card)]">
      <h2 id="lib-chart" className="text-lg font-semibold">{t("lib.chart.h")}</h2>
      <p className="text-sm text-muted">{t("lib.chart.sub")}</p>
      <div className="mt-3" style={{ height: rows.length * 30 + 40 }} role="img" aria-label={t("lib.chart.h")}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }} barSize={16}>
            <XAxis type="number" tick={{ fontSize: 14, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v.toLocaleString("en-IN")} />
            <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 14, fill: "var(--text)" }} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: "var(--surface-2)" }} contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 10, fontSize: 14 }} formatter={(v) => `₹${Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 })} crore`} />
            <Bar dataKey="fresh" stackId="a" name={t("lib.fresh.name")} fill="var(--chart-1)" />
            <Bar dataKey="ofs" stackId="a" name={t("lib.ofs.name")} fill="var(--chart-3)" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 flex gap-5 text-sm text-muted">
        <li className="flex items-center gap-2"><span aria-hidden className="h-3 w-3 rounded-[3px]" style={{ background: "var(--chart-1)" }} />{t("lib.fresh.name")}</li>
        <li className="flex items-center gap-2"><span aria-hidden className="h-3 w-3 rounded-[3px]" style={{ background: "var(--chart-3)" }} />{t("lib.ofs.name")}</li>
      </ul>
    </section>
  );
}
