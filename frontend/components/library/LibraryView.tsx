"use client";

import { MagnifyingGlass, X } from "@phosphor-icons/react";
import Image from "next/image";
import Link from "next/link";
import { useMemo, useState, useSyncExternalStore } from "react";
import { LibraryChart } from "./LibraryChart";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { useIpos } from "@/lib/api/hooks";
import { filterSortIpos, type FilterKey, type SortKey } from "@/lib/library";
import { useT } from "@/lib/useT";
import { getItemMigrating } from "@/lib/legacyStorage";
import { IpoRow } from "./IpoRow";

const HINT_KEY = "vd_hint_library";
const hintListeners = new Set<() => void>();
const hintSeen = () => {
  try {
    return getItemMigrating(localStorage, HINT_KEY) === "1";
  } catch {
    return false;
  }
};
const dismissHint = () => {
  try {
    localStorage.setItem(HINT_KEY, "1");
  } catch {
    /* storage blocked: the hint stays for this session only */
  }
  hintListeners.forEach((l) => l());
};

function FirstVisitHint() {
  const { t } = useT();
  const seen = useSyncExternalStore(
    (cb) => {
      hintListeners.add(cb);
      return () => hintListeners.delete(cb);
    },
    hintSeen,
    () => true,
  );
  if (seen) return null;
  return (
    <div className="mb-6 flex items-start justify-between gap-3 rounded-[10px] border border-rule bg-surface px-4 py-3 text-sm">
      <p>
        {t("lib.hint")}{" "}
        <Link href="/ipos/ather-energy-2025" onClick={dismissHint} className="text-accent-ink underline underline-offset-2">
          {t("lib.hintLink")}
        </Link>
      </p>
      <button
        type="button"
        onClick={dismissHint}
        aria-label={t("banner.dismiss")}
        className="-my-2 -mr-2 inline-flex h-11 w-11 shrink-0 items-center justify-center text-muted hover:text-text"
      >
        <X size={18} />
      </button>
    </div>
  );
}

const SORTS: SortKey[] = ["newest", "largest", "az"];
const FILTERS: FilterKey[] = ["all", "fresh", "ofs"];

export function LibraryView() {
  const { t } = useT();
  const { data, error, isPending, refetch } = useIpos();
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");
  const [filter, setFilter] = useState<FilterKey>("all");

  const rows = useMemo(() => (data ? filterSortIpos(data, { query, sort, filter }) : []), [data, query, sort, filter]);

  return (
    <div className="py-10 md:py-14">
      <header className="mb-8 max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-tight">{t("lib.title")}</h1>
        {data && <p className="mt-2 text-muted">{t("lib.sub", { n: data.length })}</p>}
      </header>

      <FirstVisitHint />
      {data && <LibraryChart ipos={data} />}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="relative min-w-[16rem] flex-1">
          <span className="sr-only-keep">{t("lib.search")}</span>
          <MagnifyingGlass size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("lib.search")}
            className="h-11 w-full rounded-[6px] border border-rule bg-surface pl-10 pr-3 placeholder:text-muted"
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-muted">
          <span className="sr-only-keep">{t("lib.sort.label")}</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="h-11 rounded-[6px] border border-rule bg-surface px-3 text-text"
          >
            {SORTS.map((s) => (
              <option key={s} value={s}>
                {t(`lib.sort.${s}`)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div role="group" aria-label={t("lib.filter.all")} className="mb-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className={`h-10 rounded-[6px] border px-4 text-sm ${
              filter === f ? "border-stamp bg-stamp/10 font-medium text-text" : "border-rule text-muted hover:text-text"
            }`}
          >
            {t(`lib.filter.${f}`)}
          </button>
        ))}
      </div>

      {error ? (
        <ErrorBlock error={error} onRetry={() => void refetch()} />
      ) : isPending ? (
        <div aria-busy="true" aria-label={t("loading")} className="space-y-px">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="flex items-center justify-between gap-8 border-b border-rule px-2 py-5">
              <div className="w-1/3 space-y-2">
                <div className="skeleton h-6 w-full" />
                <div className="skeleton h-4 w-1/2" />
              </div>
              <div className="skeleton hidden h-4 w-1/6 md:block" />
              <div className="skeleton hidden h-8 w-1/6 md:block" />
              <div className="skeleton h-4 w-1/5" />
            </div>
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="grid items-center gap-8 py-12 md:grid-cols-[minmax(0,1fr)_280px]">
          <div>
          <p className="max-w-xl text-lg">{t("lib.empty", { query })}</p>
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setFilter("all");
            }}
            className="mt-4 h-11 rounded-[6px] border border-rule bg-surface-2 px-4 text-sm font-medium hover:border-stamp"
          >
            {t("lib.clear")}
          </button>
          </div>
          <Image src="/images/empty-state.webp" alt="A blank sheet of paper and a pencil on a clean desk." width={800} height={600} sizes="280px" className="hidden aspect-[4/3] w-full rounded-[6px] border border-rule object-cover md:block" />
        </div>
      ) : (
        <ul className="border-t border-rule">
          {rows.map((i) => (
            <IpoRow key={i.id} ipo={i} />
          ))}
        </ul>
      )}
    </div>
  );
}
