"use client";

import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CheckCircle, Clock, Minus, Warning, WarningOctagon } from "@phosphor-icons/react";
import type { StringKey } from "@/lib/copy";
import { formatMoney, type Unit } from "@/lib/format";
import { anchorFor, flagTitleKey, statusKey, type FlagStatus, type RiskLevel } from "@/lib/report";
import { byPeriod, cell, FY_ORDER, fyLabels, type Sod } from "@/lib/sod";
import { useT } from "@/lib/useT";

export const SHIFT: Record<Unit, number> = { crore: 1e7, million: 1e6, lakh: 1e5, full: 1 };
const AXIS = { fontSize: 14, fill: "var(--text-muted)" } as const;
const TIP = { background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 10, fontSize: 14, boxShadow: "var(--shadow-float)" } as const;

// ---- risk level gauge -----------------------------------------------------------------------

const LEVEL_COLOUR = { low: "var(--ok)", medium: "var(--query)", high: "var(--bad)" } as const;

/** Half-circle gauge: three bands sized by the thresholds, a needle at the score. The word and icon carry the level. */
export function RiskGauge({ level }: { level: RiskLevel }) {
  const { t } = useT();
  const lo = level.thresholds?.low_below ?? 0.2;
  const hi = level.thresholds?.high_from ?? 0.4;
  const max = Math.max(hi * 1.75, level.score * 1.05, 0.01);
  const ang = (v: number) => Math.PI * (1 - Math.min(1, v / max));
  const pt = (v: number, r: number) => `${100 + r * Math.cos(ang(v))},${100 - r * Math.sin(ang(v))}`;
  const arc = (a: number, b: number) => `M ${pt(a, 80)} A 80 80 0 0 1 ${pt(b, 80)}`;
  const needle = pt(level.score, 68);
  return (
    <figure aria-label={t("rl.title", { level: t(`rl.${level.level}`) })} className="mx-auto w-full max-w-[280px]">
      <svg viewBox="0 0 200 118" role="img" aria-label={t("rl.gauge")} className="w-full">
        <path d={arc(0, lo)} stroke="var(--ok)" strokeWidth="16" fill="none" strokeLinecap="butt" opacity={level.level === "low" ? 1 : 0.28} />
        <path d={arc(lo, hi)} stroke="var(--query)" strokeWidth="16" fill="none" opacity={level.level === "medium" ? 1 : 0.28} />
        <path d={arc(hi, max)} stroke="var(--bad)" strokeWidth="16" fill="none" opacity={level.level === "high" ? 1 : 0.28} />
        <line x1="100" y1="100" x2={needle.split(",")[0]} y2={needle.split(",")[1]} stroke="var(--text)" strokeWidth="3" strokeLinecap="round" />
        <circle cx="100" cy="100" r="6" fill="var(--text)" />
      </svg>
      <figcaption className="-mt-1 grid grid-cols-3 text-center text-sm">
        {(["low", "medium", "high"] as const).map((l) => (
          <span key={l} className={level.level === l ? "font-bold" : "text-muted"} style={level.level === l ? { color: LEVEL_COLOUR[l] } : undefined}>
            {t(`rl.${l}`)}
          </span>
        ))}
      </figcaption>
      <p className="mt-2 text-center text-sm text-muted">{t("rl.points", { p: level.points, m: level.max_points })}</p>
    </figure>
  );
}

// ---- financials -----------------------------------------------------------------------------

/** Revenue and profit bars per fiscal year (and the stub), with PAT margin as a line on the right axis. */
export function FinChart({ sod, unit }: { sod: Sod; unit: Unit }) {
  const { t } = useT();
  const labels = fyLabels(sod);
  const rev = byPeriod(sod.financials.revenue);
  const pat = byPeriod(sod.financials.profit_after_tax);
  const rows: { name: string; revenue: number | null; pat: number | null; margin: number | null }[] = [];
  for (const p of FY_ORDER) {
    const r = cell(rev.fy[p] ?? null, unit).n;
    const q = cell(pat.fy[p] ?? null, unit).n;
    if (r === null && q === null) continue;
    rows.push({ name: labels[p], revenue: r === null ? null : r / SHIFT[unit], pat: q === null ? null : q / SHIFT[unit], margin: r && q !== null ? (q / r) * 100 : null });
  }
  const sr = cell(rev.stub, unit).n;
  const sq = cell(pat.stub, unit).n;
  if (sr !== null || sq !== null) rows.push({ name: t("fin.stub"), revenue: sr === null ? null : sr / SHIFT[unit], pat: sq === null ? null : sq / SHIFT[unit], margin: sr && sq !== null ? (sq / sr) * 100 : null });
  if (rows.filter((r) => r.revenue !== null).length < 2) return null;
  const unitWord = t(`unit.${unit}`);
  const fmt = (v: number) => formatMoney(v * SHIFT[unit], unit).replace(/\.00(?= )/, "");
  const showMargin = rows.some((r) => r.margin !== null);
  return (
    <section aria-labelledby="fin-chart" className="rounded-[16px] border border-rule bg-surface p-5 shadow-[var(--shadow-card)]">
      <h3 id="fin-chart" className="text-lg font-semibold">{t("fin.chart")}</h3>
      <p className="text-sm text-muted">{t("fin.chart.sub", { unit: unitWord })}</p>
      <div className="mt-3 h-[300px]" role="img" aria-label={t("fin.chart")}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--rule)" />
            <XAxis dataKey="name" tick={AXIS} axisLine={{ stroke: "var(--rule)" }} tickLine={false} />
            <YAxis yAxisId="l" tick={AXIS} axisLine={false} tickLine={false} width={84} tickFormatter={(v: number) => v.toLocaleString("en-IN", { maximumFractionDigits: 0 })} />
            {showMargin && <YAxis yAxisId="r" orientation="right" tick={AXIS} axisLine={false} tickLine={false} width={48} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />}
            <Tooltip contentStyle={TIP} formatter={(v, n) => (n === t("fin.margin") ? `${Number(v).toFixed(1)}%` : fmt(Number(v)))} />
            <Legend wrapperStyle={{ fontSize: 14 }} />
            <Bar yAxisId="l" dataKey="revenue" name={t("fin.row.revenue")} fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
            <Bar yAxisId="l" dataKey="pat" name={t("fin.row.profit_after_tax")} fill="var(--chart-2)" radius={[6, 6, 0, 0]} />
            {showMargin && <Line yAxisId="r" dataKey="margin" name={t("fin.margin")} stroke="var(--chart-5)" strokeWidth={2.5} dot={{ r: 4, fill: "var(--chart-5)" }} connectNulls />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

// ---- shareholding and proceeds ----------------------------------------------------------------

/** Promoter holding before and after the offer as stacked bars (promoters / everyone else). */
export function ShareholdingChart({ pre, post }: { pre: number | null; post: number | null }) {
  const { t } = useT();
  const data = [
    ...(pre !== null ? [{ name: t("ov.promoterPre"), promoters: pre, others: Math.max(0, 100 - pre) }] : []),
    ...(post !== null ? [{ name: t("ov.promoterPost"), promoters: post, others: Math.max(0, 100 - post) }] : []),
  ];
  if (data.length === 0) return null;
  return (
    <div className="h-[132px]" role="img" aria-label={t("ov.promoter")}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 0 }} barSize={26}>
          <XAxis type="number" domain={[0, 100]} tick={AXIS} tickFormatter={(v: number) => `${v}%`} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" tick={AXIS} width={130} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={TIP} formatter={(v) => `${Number(v).toFixed(1)}%`} />
          <Bar dataKey="promoters" name={t("ov.promoter")} stackId="s" fill="var(--chart-1)" radius={[6, 0, 0, 6]} />
          <Bar dataKey="others" name={t("ov.others")} stackId="s" fill="var(--chart-3)" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Fresh issue against offer for sale: who receives the money. Hidden unless both amounts are known. */
export function ProceedsSplit({ fresh, ofs }: { fresh: number | null; ofs: number | null }) {
  const { t } = useT();
  if (fresh === null || ofs === null || fresh + ofs <= 0) return null;
  const total = fresh + ofs;
  const f = (fresh / total) * 100;
  return (
    <section aria-labelledby="ov-proceeds">
      <h2 id="ov-proceeds" className="text-xl font-semibold tracking-tight">{t("ov.proceeds")}</h2>
      <div role="img" aria-label={t("ov.proceeds.aria", { f: f.toFixed(0), o: (100 - f).toFixed(0) })} className="mt-3 flex h-8 overflow-hidden rounded-[10px]">
        {f > 0 && <div style={{ width: `${f}%`, background: "var(--chart-1)" }} />}
        {f < 100 && <div style={{ width: `${100 - f}%`, background: "var(--chart-3)" }} />}
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-4 text-base">
        <div>
          <dt className="flex items-center gap-2 text-muted"><span aria-hidden className="h-3 w-3 rounded-[3px]" style={{ background: "var(--chart-1)" }} />{t("ov.proceeds.fresh")}</dt>
          <dd className="num text-lg font-semibold">₹{fresh.toLocaleString("en-IN")} crore · {f.toFixed(0)}%</dd>
        </div>
        <div>
          <dt className="flex items-center gap-2 text-muted"><span aria-hidden className="h-3 w-3 rounded-[3px]" style={{ background: "var(--chart-3)" }} />{t("ov.proceeds.ofs")}</dt>
          <dd className="num text-lg font-semibold">₹{ofs.toLocaleString("en-IN")} crore · {(100 - f).toFixed(0)}%</dd>
        </div>
      </dl>
    </section>
  );
}

// ---- red-flag status grid -----------------------------------------------------------------------

const ALL_FLAGS = Array.from({ length: 13 }, (_, i) => `RF${String(i + 1).padStart(2, "0")}`);
type Tile = "ok" | "watch" | "concern" | "na" | "pending";
const TILE_STYLE: Record<Tile, { bg: string; fg: string }> = {
  ok: { bg: "var(--ok-soft)", fg: "var(--ok)" },
  watch: { bg: "var(--query-soft)", fg: "var(--query)" },
  concern: { bg: "var(--bad-soft)", fg: "var(--bad)" },
  na: { bg: "var(--surface-2)", fg: "var(--text-muted)" },
  pending: { bg: "transparent", fg: "var(--text-muted)" },
};

function TileIcon({ tile }: { tile: Tile }) {
  const p = { size: 20, "aria-hidden": true as const, weight: "bold" as const, color: TILE_STYLE[tile].fg };
  if (tile === "ok") return <CheckCircle {...p} />;
  if (tile === "watch") return <Warning {...p} />;
  if (tile === "concern") return <WarningOctagon {...p} />;
  if (tile === "pending") return <Clock {...p} />;
  return <Minus {...p} />;
}

/** All 13 checks at a glance: decided (OK / Watch / Concern), not available, pending. Colour, icon and word together. */
export function FlagGrid({ flags, onGo }: { flags: { id: string; status: FlagStatus }[]; onGo?: (hash: string) => void }) {
  const { t } = useT();
  if (flags.length === 0) return null;
  const known = new Map(flags.map((f) => [f.id, f.status]));
  const tileOf = (id: string): Tile => {
    const s = known.get(id);
    if (!s) return "pending";
    return s === "not_available" || s === "not_applicable" ? "na" : s;
  };
  const word = (tile: Tile, id: string) => (tile === "pending" ? t("rf.group.pending") : tile === "na" ? t("rf.not_available") : t(statusKey(known.get(id) as FlagStatus)));
  const counts = (["concern", "watch", "ok", "na", "pending"] as Tile[]).map((k) => ({ k, n: ALL_FLAGS.filter((id) => tileOf(id) === k).length })).filter((c) => c.n > 0);
  return (
    <div>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
        {counts.map((c) => (
          <li key={c.k} className="flex items-center gap-1.5">
            <TileIcon tile={c.k} />
            <span className="num font-semibold">{c.n}</span> {c.k === "na" ? t("rf.not_available") : c.k === "pending" ? t("rf.group.pending") : t(`rf.${c.k}` as StringKey)}
          </li>
        ))}
      </ul>
      <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {ALL_FLAGS.map((id) => {
          const tile = tileOf(id);
          const st = TILE_STYLE[tile];
          const title = flagTitleKey(id) ? t(flagTitleKey(id) as StringKey) : id;
          const inner = (
            <>
              <TileIcon tile={tile} />
              <span className="min-w-0">
                <span className="block text-sm font-medium leading-snug">{title}</span>
                <span className="block text-sm" style={{ color: st.fg }}>{word(tile, id)}</span>
              </span>
            </>
          );
          return (
            <li key={id}>
              {onGo && tile !== "pending" ? (
                <button type="button" onClick={() => onGo(`#${anchorFor("redflag", id)}`)} className="flex h-full w-full items-start gap-2 rounded-[12px] border border-rule p-3 text-left hover:border-stamp" style={{ background: st.bg }}>
                  {inner}
                </button>
              ) : (
                <div className={`flex h-full items-start gap-2 rounded-[12px] p-3 ${tile === "pending" ? "border border-dashed border-rule" : "border border-rule"}`} style={{ background: st.bg }}>
                  {inner}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
