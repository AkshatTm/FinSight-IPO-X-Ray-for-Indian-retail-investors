// The "Summary of the Offer Document" block of a report (docs/final/CONTRACT.md). The API types
// `sod` as an open object, so it is read defensively here: anything missing or malformed is
// dropped and the section that needs it is hidden. Nothing in this file throws.

import { formatMoney, formatPercent, formatRupee, type Unit } from "@/lib/format";

export interface SodValue {
  kind: string;
  value_inr?: string | null;
  value?: string | number | null;
  raw?: string | null;
  unit?: string | null;
}
export interface SodEvidence {
  page?: number | null;
  sentence?: string | null;
}
export interface SodEntry {
  key: string;
  period: string;
  status: "found" | "stated_zero" | "not_found";
  value: SodValue | null;
  evidence: SodEvidence | null;
}
export interface SodRatio {
  key: string;
  period: string;
  value: string | null;
  unit: string | null;
  formula: string | null;
  pages: number[];
  status: "computed" | "as_printed" | "not_available";
  reason: string | null;
}
export interface SodStrength {
  heading: string;
  sentence: string;
  page: number | null;
}
export interface Sod {
  has_sod: boolean;
  financials: Record<string, SodEntry[]>;
  derived: SodRatio[];
  promoter_holding_pre: SodEntry | null;
  promoter_holding_post: SodEntry | null;
  strengths: SodStrength[];
}

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);
const str = (x: unknown): string | null => (typeof x === "string" && x.trim() ? x : null);
const numOrNull = (x: unknown): number | null => (typeof x === "number" && Number.isFinite(x) ? x : null);

function entry(x: unknown): SodEntry | null {
  if (!isObj(x)) return null;
  const status = x.status === "found" || x.status === "stated_zero" || x.status === "not_found" ? x.status : "not_found";
  const v = isObj(x.value) ? (x.value as unknown as SodValue) : null;
  const ev = isObj(x.evidence) ? (x.evidence as SodEvidence) : null;
  return { key: str(x.key) ?? "", period: str(x.period) ?? "", status, value: v, evidence: ev };
}

function ratio(x: unknown): SodRatio | null {
  if (!isObj(x) || !str(x.key)) return null;
  const status = x.status === "computed" || x.status === "as_printed" ? x.status : "not_available";
  return {
    key: String(x.key),
    period: str(x.period) ?? "latest",
    value: x.value == null ? null : String(x.value),
    unit: str(x.unit),
    formula: str(x.formula),
    pages: Array.isArray(x.pages) ? x.pages.filter((p): p is number => typeof p === "number") : [],
    status,
    reason: str(x.reason),
  };
}

/** Parse `report.sod`; null when absent or not an object (an older report). */
export function parseSod(raw: unknown): Sod | null {
  if (!isObj(raw)) return null;
  const financials: Record<string, SodEntry[]> = {};
  if (isObj(raw.financials)) {
    for (const [k, rows] of Object.entries(raw.financials)) {
      if (!Array.isArray(rows)) continue;
      const list = rows.map(entry).filter((e): e is SodEntry => e !== null);
      if (list.length) financials[k] = list;
    }
  }
  const strengths = (Array.isArray(raw.strengths) ? raw.strengths : [])
    .filter(isObj)
    .map((s) => ({ heading: str(s.heading) ?? "", sentence: str(s.sentence) ?? "", page: numOrNull(s.page) }))
    .filter((s) => s.heading || s.sentence);
  return {
    has_sod: raw.has_sod !== false,
    financials,
    derived: (Array.isArray(raw.derived) ? raw.derived : []).map(ratio).filter((r): r is SodRatio => r !== null),
    promoter_holding_pre: entry(raw.promoter_holding_pre),
    promoter_holding_post: entry(raw.promoter_holding_post),
    strengths,
  };
}

// ---- formatting -----------------------------------------------------------------------------

/** "−₹3.30": the minus goes before the rupee sign, and is a real minus. */
export const signed = (text: string) => text.replace(/^-/, "−");

export interface Cell {
  /** Text to show; null when the document does not state it. */
  text: string | null;
  page: number | null;
  /** Numeric value in rupees (or percent) for charts; null when not found. */
  n: number | null;
}

const MISSING: Cell = { text: null, page: null, n: null };

export function cell(e: SodEntry | null | undefined, unit: Unit, perShare = false): Cell {
  if (!e) return MISSING;
  const page = e.evidence?.page ?? null;
  if (e.status === "stated_zero") return { text: "0", page, n: 0 };
  if (e.status !== "found" || !e.value) return MISSING;
  const v = e.value;
  try {
    if (v.kind === "money" && v.value_inr != null) {
      const n = Number(v.value_inr);
      return { text: signed(perShare ? formatRupee(v.value_inr) : formatMoney(v.value_inr, unit)), page, n: Number.isFinite(n) ? n : null };
    }
    if (v.kind === "percent" && v.value != null) {
      const n = Number(v.value);
      return Number.isFinite(n) ? { text: signed(formatPercent(n)), page, n } : MISSING;
    }
    if (v.kind === "count" && v.value != null) {
      return { text: String(v.value), page, n: Number(v.value) };
    }
  } catch {
    return MISSING;
  }
  return MISSING;
}

const FY_ORDER = ["latest-2", "latest-1", "latest"] as const;
export type FyPeriod = (typeof FY_ORDER)[number];
export { FY_ORDER };

/** Entries of a row keyed by period. The stub is whatever period is not latest/-1/-2 (free text). */
export function byPeriod(rows: SodEntry[] | undefined): { fy: Partial<Record<FyPeriod, SodEntry>>; stub: SodEntry | null } {
  const fy: Partial<Record<FyPeriod, SodEntry>> = {};
  let stub: SodEntry | null = null;
  for (const r of rows ?? []) {
    if ((FY_ORDER as readonly string[]).includes(r.period)) fy[r.period as FyPeriod] = r;
    else if (!stub || (stub.status !== "found" && r.status === "found")) stub = r;
  }
  return { fy, stub };
}

/** Fiscal-year labels. Reads the year printed in the evidence of the latest column ("… — 2026: …"). */
export function fyLabels(sod: Sod): Record<FyPeriod, string> {
  let year: number | null = null;
  for (const rows of Object.values(sod.financials)) {
    const s = rows.find((r) => r.period === "latest")?.evidence?.sentence;
    const m = s ? /\b(20\d\d)\b/.exec(s) : null;
    if (m) {
      year = Number(m[1]);
      break;
    }
  }
  if (year === null) return { "latest-2": "Two years back", "latest-1": "Previous year", latest: "Latest year" };
  return { "latest-2": `FY${year - 2}`, "latest-1": `FY${year - 1}`, latest: `FY${year}` };
}

export const hasFinancials = (sod: Sod | null): sod is Sod => !!sod && Object.keys(sod.financials).length > 0;

/** Text of a derived ratio, or null when not available. */
export function ratioText(r: SodRatio, unit: Unit): string | null {
  if (r.status === "not_available" || r.value == null) return null;
  const n = Number(r.value);
  if (!Number.isFinite(n)) return null;
  if (r.unit === "%") return signed(`${n.toFixed(1)}%`);
  if (r.unit === "x") return `${n.toFixed(2)}×`;
  if (r.unit === "₹") return signed(formatMoney(r.value, unit));
  return r.value;
}

/** Issuer row of `facts_summary.peers` (RoNW, P/E, NAV from Basis for Offer Price). */
export function issuerPeer(facts: unknown): { ronw: string | null; pe: string | null; nav: string | null; page: number | null } | null {
  if (!isObj(facts) || !Array.isArray(facts.peers)) return null;
  const row = facts.peers.find((p) => isObj(p) && p.is_issuer === true);
  if (!isObj(row)) return null;
  const ev = isObj(row.evidence) ? numOrNull(row.evidence.page) : null;
  const s = (x: unknown) => (x == null || x === "" ? null : String(x));
  return { ronw: s(row.ronw), pe: s(row.pe), nav: s(row.nav), page: ev };
}
