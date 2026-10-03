import type { Schemas } from "@/lib/api/client";
import { formatMoney, formatPercent, type Unit } from "@/lib/format";

export type CompareData = Schemas["Compare"];
export type Peer = Schemas["Peer"];
export type Metric = Schemas["ComparePercentile"]["metric"];

/** Issuer first, then peers in document order. */
export function orderPeers(peers: readonly Peer[]): Peer[] {
  return [...peers.filter((p) => p.is_issuer), ...peers.filter((p) => !p.is_issuer)];
}

/** A peer-table cell: "—" when the document leaves it blank. */
export function peerCell(value: string | null | undefined, kind: "pe" | "eps" | "ronw" | "nav"): string {
  if (value == null) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  if (kind === "ronw") return formatPercent(n);
  if (kind === "pe") return n.toFixed(1);
  return `₹${n.toFixed(2)}`;
}

/** A metric's value as the reader sees it (issue size in the chosen money unit). */
export function metricValue(metric: Metric, value: number, unit: Unit = "crore"): string {
  switch (metric) {
    case "issue_size_inr":
      return formatMoney(value, unit);
    case "ofs_share":
      return formatPercent(value * 100);
    case "insider_price_gap":
      return `${value.toFixed(1)}×`;
    case "pe":
      return value.toFixed(1);
  }
}

/** Whole-number percentile for "Higher than {p}% of past IPOs" (never shows 100 or -0). */
export function roundPercentile(p: number): number {
  return Math.min(99, Math.max(0, Math.round(p)));
}

/** The page of the peer table, from the first peer with evidence. */
export function sourcePage(peers: readonly Peer[]): number | null {
  return peers.find((p) => p.evidence)?.evidence?.page ?? null;
}
