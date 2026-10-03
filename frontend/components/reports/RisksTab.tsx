"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, apiSend, type Schemas } from "@/lib/api/client";
import { anchorFor, categoryKey, plainState, unusualness, type Risk, type RisksPage } from "@/lib/report";
import { useT } from "@/lib/useT";

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

  return (
    <section aria-labelledby="rk-title" className="space-y-5">
      <header>
        <h2 id="rk-title" className="text-xl font-semibold">{t("rk.title")}</h2>
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
              className={`rounded-full border px-3 py-1 text-sm ${sort === s.id ? "border-stamp bg-stamp/10 font-medium" : "border-rule hover:bg-surface-2"}`}
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
          className="min-w-[200px] flex-1 rounded-full border border-rule bg-surface px-4 py-1.5 text-sm"
        />
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" checked={unusualOnly} onChange={(e) => setUnusualOnly(e.target.checked)} />
          {t("rk.unusualOnly")}
        </label>
      </div>

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
              className={`rounded-full border px-3 py-1 text-xs ${on ? "border-stamp bg-stamp/10 font-medium" : "border-rule hover:bg-surface-2"}`}
            >
              {t(key)} <span className="text-muted">{g.count}</span>
            </button>
          );
        })}
      </div>

      {page.risks.length === 0 ? (
        <p className="text-sm text-muted">{t("rk.none")}</p>
      ) : (
        <ul className="space-y-3">
          {page.risks.map((r) => (
            <RiskCard key={r.rid} docId={docId} risk={r} queued={queued.has(r.rid)} onAsk={onAsk} />
          ))}
        </ul>
      )}
      <p className="text-xs text-muted">{t("rk.footnote")}</p>
    </section>
  );
}

function RiskCard({ docId, risk, queued, onAsk }: { docId: string; risk: Risk; queued: boolean; onAsk?: (risk: Risk) => void }) {
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
    <li id={anchorFor("risk", risk.rid)} className="scroll-mt-24 rounded-[10px] border border-rule bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {cat && <span className="rounded-full bg-surface-2 px-2 py-0.5">{t(cat)}</span>}
        {risk.seriousness && <span className="text-muted">{t(`rk.sev.${risk.seriousness}`)}</span>}
        {unusual && <span className={`rounded-full px-2 py-0.5 ${unusual.key === "rk.unusual" ? "bg-stamp/15 font-medium" : "bg-surface-2"}`}>{t(unusual.key, { x: unusual.x })}</span>}
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
          <button type="button" className="rounded-full border border-rule px-3 py-1 text-sm hover:bg-surface-2" onClick={() => explain.mutate()}>
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
          <span className="mt-2 inline-block rounded-full border border-rule px-2 text-xs text-muted">{t("rf.page", { p: pages })}</span>
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
        <button type="button" className="mt-3 rounded-full border border-rule px-3 py-1 text-sm hover:bg-surface-2" onClick={() => onAsk(risk)}>
          {t("rk.askAbout")}
        </button>
      )}
    </li>
  );
}
