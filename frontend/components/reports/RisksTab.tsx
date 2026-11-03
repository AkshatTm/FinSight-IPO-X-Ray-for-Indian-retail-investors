"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, apiSend, type Schemas } from "@/lib/api/client";
import { anchorFor, categoryKey, plainState, unusualness, type Risk, type RisksPage } from "@/lib/report";
import { useT } from "@/lib/useT";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Sort = "importance" | "order" | "category";
const SORTS: { id: Sort; key: "rk.sortImportance" | "rk.sortOrder" | "rk.sortCategory" }[] = [
  { id: "importance", key: "rk.sortImportance" },
  { id: "order", key: "rk.sortOrder" },
  { id: "category", key: "rk.sortCategory" },
];

/** Risks tab (B05 §5.5): sort, category chips, search, unusual-only, and one card per risk. */
export function RisksTab({ docId, focus, onAsk }: { docId: string; focus?: string | null; onAsk?: (risk: Risk) => void }) {
  const { t } = useT();
  const [sort, setSort] = useState<Sort>("importance");
  const [category, setCategory] = useState<Risk["category"] | "">("");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [unusualOnly, setUnusualOnly] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setQ(search.trim()), 250);
    return () => clearTimeout(id);
  }, [search]);

  const params = new URLSearchParams({ sort });
  if (category) params.set("category", category);
  if (q) params.set("q", q);
  if (unusualOnly) params.set("unusual_only", "true");
  const list = useQuery({
    queryKey: ["risks", docId, sort, category, q, unusualOnly],
    queryFn: () => apiGet<RisksPage>(`/api/docs/${docId}/risks?${params}`),
    // While rewrites are queued, look again every few seconds so they appear as they land.
    refetchInterval: (query) => ((query.state.data?.queued?.length ?? 0) > 0 ? 5000 : false),
  });

  useEffect(() => {
    if (!focus || !list.data) return;
    document.getElementById(focus.replace(/^#/, ""))?.scrollIntoView({ block: "start" });
  }, [focus, list.data]);

  if (list.isPending) return <div aria-busy className="h-48 animate-pulse rounded-[10px] bg-surface-2 motion-reduce:animate-none" />;
  if (list.isError) return <ErrorBlock error={list.error} onRetry={() => void list.refetch()} />;
  const page = list.data;
  const queued = new Set(page.queued ?? []);
  const TOP = 7;
  const filtered = !!category || !!q || unusualOnly;
  const collapsed = !showAll && !filtered && sort === "importance" && page.risks.length > TOP;
  const visible = collapsed ? page.risks.slice(0, TOP) : page.risks;

  return (
    <section aria-labelledby="rk-title" className="space-y-5">
      <header>
        <h2 id="rk-title" className="text-xl font-semibold tracking-tight">{t("rk.title")}</h2>
        <p className="mt-1 text-sm text-muted">{t("rk.sub", { n: page.n_total })}</p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div role="radiogroup" aria-label={t("rk.sortImportance")} className="flex flex-wrap gap-1">
          {SORTS.map((s) => (
            <button
              key={s.id}
              type="button"
              role="radio"
              aria-checked={sort === s.id}
              onClick={() => setSort(s.id)}
              className={`rounded-[6px] border px-3 py-1 text-sm ${sort === s.id ? "border-stamp bg-stamp/10 font-medium" : "border-rule hover:bg-surface-2"}`}
            >
              {t(s.key)}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("rk.search")}
          aria-label={t("rk.search")}
          className="min-w-[200px] flex-1 rounded-[6px] border border-rule bg-surface px-3 py-1.5 text-sm"
        />
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" checked={unusualOnly} onChange={(e) => setUnusualOnly(e.target.checked)} />
          {t("rk.unusualOnly")}
        </label>
      </div>

      {!filtered && <RiskCharts groups={page.groups ?? []} risks={page.risks} />}

      <div role="group" aria-label={t("rk.title")} className="flex flex-wrap gap-2">
        {(page.groups ?? []).map((g) => {
          const key = categoryKey(g.category);
          if (!key || !g.category) return null;
          const on = category === g.category;
          return (
            <button
              key={g.category}
              type="button"
              aria-pressed={on}
              onClick={() => setCategory(on ? "" : g.category)}
              className={`rounded-[6px] border px-2.5 py-1 text-xs ${on ? "border-stamp bg-stamp/10 font-medium" : "border-rule hover:bg-surface-2"}`}
            >
              {t(key)} <span className="text-muted">{g.count}</span>
            </button>
          );
        })}
      </div>

      {page.risks.length === 0 ? (
        <p className="text-sm text-muted">{t("rk.none")}</p>
      ) : (
        <>
          {collapsed && <p className="text-sm text-muted">{t("rk.top", { n: TOP })}</p>}
          <ul className="divide-y divide-rule border-y border-rule">
            {visible.map((r, i) => (
              <RiskCard key={r.rid} docId={docId} risk={r} queued={queued.has(r.rid)} onAsk={onAsk} rank={sort === "importance" && !filtered ? i + 1 : undefined} />
            ))}
          </ul>
          {(collapsed || showAll) && page.risks.length > TOP && !filtered && sort === "importance" && (
            <button type="button" onClick={() => setShowAll(!showAll)} className="rounded-[6px] border border-rule px-4 py-2 text-sm font-medium hover:bg-surface-2">
              {showAll ? t("rk.showTop", { n: TOP }) : t("rk.showAll", { n: page.n_total })}
            </button>
          )}
        </>
      )}
      <p className="text-xs text-muted">{t("rk.footnote")}</p>
    </section>
  );
}

const SEV = { high: { c: "var(--bad)", w: 100 }, medium: { c: "var(--query)", w: 62 }, low: { c: "var(--ok)", w: 28 } } as const;

/** Severity as a bar with its word, so colour is never the only signal. */
function SeverityBar({ level, importance }: { level?: Risk["seriousness"]; importance?: number | null }) {
  const { t } = useT();
  if (!level) return null;
  const s = SEV[level];
  return (
    <div className="flex min-w-0 flex-1 items-center gap-3 text-sm">
      <span className="h-2 w-full max-w-[200px] overflow-hidden rounded-full bg-surface-2" role="img" aria-label={t(`rk.sev.${level}`)}>
        <span className="block h-full rounded-full" style={{ width: `${s.w}%`, background: s.c }} />
      </span>
      <span className="font-medium">{t(`rk.sev.${level}`)}</span>
      {importance != null && <span className="num text-muted">{Math.round(importance * 100)}/100</span>}
    </div>
  );
}

function RiskCharts({ groups, risks }: { groups: { category?: Risk["category"]; count: number }[]; risks: Risk[] }) {
  const { t } = useT();
  const cats = groups.flatMap((g) => {
    const k = g.category ? categoryKey(g.category) : null;
    return k ? [{ name: t(k), count: g.count }] : [];
  });
  const sev = (["high", "medium", "low"] as const).map((k) => ({ k, name: t(`rk.sev.${k}`), n: risks.filter((r) => r.seriousness === k).length })).filter((x) => x.n > 0);
  if (cats.length < 2 && sev.length < 2) return null;
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      {cats.length >= 2 && (
        <section aria-labelledby="rk-cat" className="rounded-[16px] border border-rule bg-surface p-5 shadow-[var(--shadow-card)]">
          <h3 id="rk-cat" className="text-lg font-semibold">{t("rk.chart.cat")}</h3>
          <p className="text-sm text-muted">{t("rk.chart.count")}</p>
          <div className="mt-2" style={{ height: cats.length * 30 + 28 }} role="img" aria-label={t("rk.chart.cat")}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cats} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 0 }} barSize={16}>
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 14, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 14, fill: "var(--text)" }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "var(--surface-2)" }} contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)", borderRadius: 10, fontSize: 14 }} />
                <Bar dataKey="count" name={t("rk.chart.count")} fill="var(--chart-1)" radius={[0, 6, 6, 0]} label={{ position: "right", fontSize: 14, fill: "var(--text)" }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
      {sev.length >= 2 && (
        <section aria-labelledby="rk-sev" className="rounded-[16px] border border-rule bg-surface p-5 shadow-[var(--shadow-card)]">
          <h3 id="rk-sev" className="text-lg font-semibold">{t("rk.chart.sev")}</h3>
          <ul className="mt-4 space-y-4">
            {sev.map((x) => (
              <li key={x.k}>
                <div className="flex items-baseline justify-between text-base"><span>{x.name}</span><span className="num font-semibold">{x.n}</span></div>
                <div className="mt-1 h-3 overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full rounded-full" style={{ width: `${(x.n / Math.max(...sev.map((y) => y.n))) * 100}%`, background: SEV[x.k].c }} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function RiskCard({ docId, risk, queued, onAsk, rank }: { docId: string; risk: Risk; queued: boolean; onAsk?: (risk: Risk) => void; rank?: number }) {
  const { t } = useT();
  const qc = useQueryClient();
  const explain = useMutation({
    mutationFn: () => apiSend<Schemas["SimplifyQueued"]>("POST", `/api/docs/${docId}/risks/${risk.rid}/simplify`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["risks", docId] }),
  });
  const state = plainState(risk, queued || explain.isPending || explain.isSuccess);
  const cat = categoryKey(risk.category);
  const unusual = unusualness(risk.novelty);
  const figures = (risk.numbers ?? []).map((n) => ("raw" in n ? n.raw : "")).filter(Boolean);
  const pages = risk.page_start === risk.page_end ? `${risk.page_start}` : `${risk.page_start}–${risk.page_end}`;
  return (
    <li id={anchorFor("risk", risk.rid)} className="scroll-mt-40 py-5">
      {rank !== undefined && rank <= 7 && (
        <div className="mb-2 flex items-center gap-3">
          <span className="num grid h-7 w-7 place-items-center rounded-full bg-band text-sm font-semibold text-on-band">{rank}</span>
          <SeverityBar level={risk.seriousness} importance={risk.importance} />
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {cat && <span className="rounded-[4px] bg-surface-2 px-2 py-0.5">{t(cat)}</span>}
        {risk.seriousness && <span className="text-muted">{t(`rk.sev.${risk.seriousness}`)}</span>}
        {unusual && <span className={`rounded-[4px] px-2 py-0.5 ${unusual.key === "rk.unusual" ? "bg-stamp/15 font-medium" : "bg-surface-2"}`}>{t(unusual.key, { x: unusual.x })}</span>}
      </div>

      <div className="mt-2">
        {state === "ready" && <p>{risk.simple}</p>}
        {state === "explaining" && (
          <div aria-busy>
            <div className="h-4 w-3/4 animate-pulse rounded bg-surface-2 motion-reduce:animate-none" />
            <p className="mt-1 text-sm text-muted">{t("rk.explaining")}</p>
          </div>
        )}
        {state === "not_queued" && (
          <button type="button" className="rounded-[6px] border border-rule px-3 py-1 text-sm hover:bg-surface-2" onClick={() => explain.mutate()}>
            {t("rk.explain")}
          </button>
        )}
        {state === "rejected" && <p className="text-sm text-muted">{t("rk.rejected")}</p>}
      </div>

      <details className="mt-3 text-sm" open={state === "rejected"}>
        <summary className="cursor-pointer">{t("rk.theirWording")}</summary>
        <div className="mt-2 max-h-[18rem] overflow-y-auto">
          <p className="font-semibold">{risk.title}</p>
          <p className="mt-1 whitespace-pre-line">{risk.body}</p>
          <span className="mt-2 inline-block rounded-[4px] border border-rule px-1.5 text-xs text-muted">{t("rf.page", { p: pages })}</span>
        </div>
      </details>

      {risk.hedging?.flag && <p className="mt-2 text-sm">{t("rk.hedging")}</p>}
      {figures.length > 0 && <p className="mt-1 text-sm text-muted">{t("rk.figures", { list: figures.join(", ") })}</p>}

      {(risk.nearest_examples ?? []).length > 0 && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer">{t("rk.similar")}</summary>
          <ul className="mt-1 space-y-1">
            {(risk.nearest_examples ?? []).slice(0, 3).map((e) => (
              <li key={`${e.company}-${e.year}-${e.title}`}>{t("rk.similarRow", { company: e.company, year: e.year, title: e.title })}</li>
            ))}
          </ul>
        </details>
      )}

      {onAsk && (
        <button type="button" className="mt-3 rounded-[6px] border border-rule px-3 py-1 text-sm hover:bg-surface-2" onClick={() => onAsk(risk)}>
          {t("rk.askAbout")}
        </button>
      )}
    </li>
  );
}
