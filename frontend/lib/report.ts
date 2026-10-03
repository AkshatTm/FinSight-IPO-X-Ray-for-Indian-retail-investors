import type { Schemas } from "@/lib/api/client";
import type { StringKey } from "@/lib/i18n";

export type RedFlag = Schemas["RedFlag"];
export type FlagStatus = RedFlag["status"];
export type Risk = Schemas["Risk"];
export type RiskLevel = Schemas["RiskLevel"];
export type RisksPage = Schemas["RisksPage"];
export type ReportOverview = Schemas["ReportOverview"];

export type FlagFilter = "all" | "concern" | "watch" | "ok" | "na";
export const FLAG_FILTERS: readonly FlagFilter[] = ["all", "concern", "watch", "ok", "na"];
const STATUS_RANK: Record<FlagStatus, number> = { concern: 0, watch: 1, ok: 2, not_available: 3, not_applicable: 3 };

/** B05 §5.4 order: Concern, Watch, OK, Not available; by RF id within each. */
export function sortFlags(flags: readonly RedFlag[]): RedFlag[] {
  return [...flags].sort((a, b) => STATUS_RANK[a.status] - STATUS_RANK[b.status] || a.id.localeCompare(b.id));
}

export function flagMatches(flag: Pick<RedFlag, "status">, filter: FlagFilter): boolean {
  if (filter === "all") return true;
  if (filter === "na") return flag.status === "not_available" || flag.status === "not_applicable";
  return flag.status === filter;
}

export function filterKey(filter: FlagFilter): StringKey {
  return filter === "all" ? "rf.all" : filter === "na" ? "rf.not_available" : (`rf.${filter}` as StringKey);
}

export function statusKey(status: FlagStatus): StringKey {
  return `rf.${status}` as StringKey;
}

/** The B05 title of a check ("RF04" → "Who gets the IPO money"); unknown ids stay as they are. */
export function flagTitleKey(id: string): StringKey | null {
  return /^RF(0[1-9]|1[0-3])$/.test(id) ? (`rf.t.${id}` as StringKey) : null;
}

/** Card sentence; a status without a B05 template falls back to B-FR-02's default line. */
export function flagSentence(flag: Pick<RedFlag, "sentence">): StringKey | string {
  return flag.sentence.trim() ? flag.sentence : "rf.missing";
}

/** "Unusual" below 10% of past IPOs, "Common" above 60%, else the plain share (B05 §5.5). */
export function unusualness(novelty: number | null | undefined): { key: StringKey; x: number } | null {
  if (novelty == null) return null;
  const x = Math.round(novelty * 100);
  if (novelty < 0.1) return { key: "rk.unusual", x };
  if (novelty > 0.6) return { key: "rk.common", x };
  return { key: "rk.inPast", x };
}

export function isUnusual(risk: Pick<Risk, "novelty">): boolean {
  return risk.novelty != null && risk.novelty < 0.1;
}

export function categoryKey(category: Risk["category"]): StringKey | null {
  return category ? (`cat.${category}` as StringKey) : null;
}

/** What the plain-English slot shows for a risk (B05 §5.5). */
export type PlainState = "ready" | "explaining" | "rejected" | "not_queued";
export function plainState(risk: Pick<Risk, "simple" | "simple_status">, queued: boolean): PlainState {
  if (risk.simple_status === "ready" && risk.simple) return "ready";
  if (risk.simple_status === "rejected") return "rejected";
  return queued ? "explaining" : "not_queued";
}

export interface OfferLineParams {
  company?: string | null;
  fresh_crore?: string | null;
  ofs_crore?: string | null;
  price?: string | null;
  doc_type?: string | null;
}

/** "The offer in one line" (B05 §5.3) as a string key + vars, or null when the numbers are missing. */
export function offerLine(p: OfferLineParams | null | undefined): { key: StringKey; vars: Record<string, string> } | null {
  if (!p) return null;
  if (p.doc_type === "drhp") return { key: "ov.offerDrhp", vars: {} };
  const fresh = Number(p.fresh_crore ?? "0");
  if (p.ofs_crore && (!p.fresh_crore || fresh === 0)) return { key: "ov.offerOfs", vars: { ofs: p.ofs_crore } };
  if (p.company && p.fresh_crore && p.ofs_crore && p.price) {
    return { key: "ov.offer", vars: { company: p.company, fresh: p.fresh_crore, ofs: p.ofs_crore, price: p.price } };
  }
  return null;
}

/** Percent of the level bar to mark (Low, Medium, High). */
export const LEVELS = ["low", "medium", "high"] as const;

/** At most 6 reasons, most points first (B05 §5.3 "Why"). */
export function topReasons(level: Pick<RiskLevel, "reasons">): RiskLevel["reasons"] {
  return [...level.reasons].sort((a, b) => b.points - a.points).slice(0, 6);
}

/** Anchor ids used by reasons and pills ("#redflag-RF03", "#risk-r12"). */
export const anchorFor = (source: "redflag" | "risk", id: string) => `${source}-${id}`;

export type Tab = "overview" | "redflags" | "risks" | "compare";
export const TABS: readonly Tab[] = ["overview", "redflags", "risks", "compare"];

/** Which tab an anchor lives on. */
export function tabForHash(hash: string): Tab | null {
  const h = hash.replace(/^#/, "");
  if (h.startsWith("redflag-")) return "redflags";
  if (h.startsWith("risk-")) return "risks";
  return (TABS as readonly string[]).includes(h) ? (h as Tab) : null;
}
