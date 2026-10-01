import type { Schemas } from "@/lib/api/client";

export type Ipo = Schemas["IpoSummary"];
export type SortKey = "newest" | "largest" | "az";
export type FilterKey = "all" | "fresh" | "ofs";

const num = (v: string | null | undefined): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

export const hasFresh = (i: Ipo) => num(i.fresh_inr) > 0;
export const isPureOfs = (i: Ipo) => !hasFresh(i) && num(i.ofs_inr) > 0;

/** Fresh and OFS as shares of the issue; null when the split is not known. */
export function splitPct(i: Ipo): { fresh: number; ofs: number } | null {
  const total = num(i.issue_size_inr) || num(i.fresh_inr) + num(i.ofs_inr);
  if (total <= 0) return null;
  const fresh = Math.min(100, (num(i.fresh_inr) / total) * 100);
  return { fresh, ofs: 100 - fresh };
}

export function filterSortIpos(
  list: Ipo[],
  opts: { query: string; sort: SortKey; filter: FilterKey },
): Ipo[] {
  const q = opts.query.trim().toLowerCase();
  const out = list.filter((i) => {
    if (q && !`${i.company} ${i.sector ?? ""}`.toLowerCase().includes(q)) return false;
    if (opts.filter === "fresh") return hasFresh(i);
    if (opts.filter === "ofs") return isPureOfs(i);
    return true;
  });
  const cmp: Record<SortKey, (a: Ipo, b: Ipo) => number> = {
    newest: (a, b) => (b.listing_date ?? "").localeCompare(a.listing_date ?? ""),
    largest: (a, b) => num(b.issue_size_inr) - num(a.issue_size_inr),
    az: (a, b) => a.company.localeCompare(b.company, "en", { sensitivity: "base" }),
  };
  return [...out].sort(cmp[opts.sort]);
}
