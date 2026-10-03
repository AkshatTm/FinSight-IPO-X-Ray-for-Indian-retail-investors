// Readers for the Phase 2 Model Lab payloads (`/api/lab/b/*`, files in eval_results/b/, B06 §5).
// Like lib/lab.ts, every reader returns null when a value is missing and the page hides that part.
// The shapes are the contract for the local eval scripts (B04 E13–E24), written down in B06 §5.

type Json = Record<string, unknown>;
const isObj = (v: unknown): v is Json => typeof v === "object" && v !== null && !Array.isArray(v);
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const get = (v: unknown, ...path: string[]): unknown => path.reduce<unknown>((n, k) => (isObj(n) ? n[k] : undefined), v);
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const pair = (v: unknown): [number, number] | null =>
  Array.isArray(v) && v.length >= 2 && num(v[0]) !== null && num(v[1]) !== null ? [v[0] as number, v[1] as number] : null;

export const pct = (x: number) => Math.round(x * 100);

// ---- 1. Splitting risks (E13) ----------------------------------------------------------------
export interface Segmentation { precision: number; recall: number; f1: number; nDocs: number; corpusF1: number | null }
export function segmentation(v: unknown): Segmentation | null {
  const [p, r, f] = [num(get(v, "precision")), num(get(v, "recall")), num(get(v, "f1"))];
  if (p === null || r === null || f === null) return null;
  return { precision: p, recall: r, f1: f, nDocs: num(get(v, "n_docs")) ?? 0, corpusF1: num(get(v, "e13b", "f1")) };
}

// ---- 2. Reading the financial checks (E14, E15) ----------------------------------------------
export interface Checks { nvm: number | null; nValues: number; accuracy: number | null; nFlags: number; labels: string[]; confusion: number[][] }
export function financialChecks(summary: unknown, redflags: unknown): Checks | null {
  const nvm = num(get(summary, "nvm"));
  const accuracy = num(get(redflags, "accuracy"));
  if (nvm === null && accuracy === null) return null;
  const labels = arr(get(redflags, "labels")).filter((l): l is string => typeof l === "string");
  const confusion = arr(get(redflags, "confusion")).map((row) => arr(row).map((c) => num(c) ?? 0));
  const square = confusion.length === labels.length && confusion.every((r) => r.length === labels.length);
  return {
    nvm,
    nValues: num(get(summary, "n")) ?? 0,
    accuracy,
    nFlags: num(get(redflags, "n")) ?? 0,
    labels: square ? labels : [],
    confusion: square ? confusion : [],
  };
}

// ---- 3. Sorting risks into categories (E16) --------------------------------------------------
export interface ClfRow { key: string; label: string; f1: number; std: number | null; seeds: number | null; n: number }
const CLF_ORDER = ["tfidf", "base", "large", "teacher"];
export function classifierLadder(v: unknown): ClfRow[] {
  const rows: ClfRow[] = [];
  for (const s of arr(get(v, "systems"))) {
    const block = isObj(get(s, "gold")) ? get(s, "gold") : isObj(get(s, "dev")) ? get(s, "dev") : s;
    const f1 = num(get(s, "macro_f1_mean")) ?? num(get(block, "macro_f1"));
    if (f1 === null) continue;
    const file = String(get(s, "file") ?? "");
    const key = file.replace(/^classifier_/, "");
    rows.push({
      key,
      label: String(get(s, "model") ?? key),
      f1,
      std: num(get(s, "macro_f1_std")),
      seeds: arr(get(s, "seeds")).length || null,
      n: num(get(block, "n")) ?? 0,
    });
  }
  const rank = (k: string) => {
    const i = CLF_ORDER.findIndex((o) => k.includes(o));
    return i < 0 ? CLF_ORDER.length : i;
  };
  return rows.sort((a, b) => rank(a.key) - rank(b.key));
}

// ---- 4. Plain-English rewrites (E18–E20) -----------------------------------------------------
export interface HumanRow { system: string; yes: number; partly: number; no: number; n: number }
export interface Rewrites { human: HumanRow[]; gradeDrop: number | null; gradeBefore: number | null; gradeAfter: number | null; rejected: number | null; nChecked: number; reasons: { key: string; n: number }[] }
export function rewrites(simplify: unknown, readability: unknown): Rewrites | null {
  const human: HumanRow[] = [];
  for (const s of arr(get(simplify, "human", "systems"))) {
    const [yes, partly, no] = [num(get(s, "yes")), num(get(s, "partly")), num(get(s, "no"))];
    if (yes === null || partly === null || no === null) continue;
    human.push({ system: String(get(s, "system") ?? "?"), yes, partly, no, n: num(get(s, "n")) ?? 0 });
  }
  const before = num(get(readability, "fkgl_original"));
  const after = num(get(readability, "fkgl_rewrite"));
  const drop = num(get(readability, "fkgl_drop")) ?? (before !== null && after !== null ? before - after : null);
  const nChecked = num(get(simplify, "checks", "n")) ?? 0;
  const rejectedN = num(get(simplify, "checks", "rejected"));
  const rejected = rejectedN !== null && nChecked > 0 ? rejectedN / nChecked : null;
  const reasonsObj = get(simplify, "checks", "reasons");
  const reasons = isObj(reasonsObj)
    ? Object.entries(reasonsObj).flatMap(([key, n]) => (num(n) !== null ? [{ key, n: n as number }] : [])).sort((a, b) => b.n - a.n)
    : [];
  if (!human.length && drop === null && rejected === null) return null;
  return { human, gradeDrop: drop, gradeBefore: before, gradeAfter: after, rejected, nChecked, reasons };
}

/** Rewrites that passed every check, across the showcase IPOs (landing "risks explained"). */
export function risksExplained(simplify: unknown): number | null {
  const n = num(get(simplify, "checks", "n"));
  const rejected = num(get(simplify, "checks", "rejected"));
  return n !== null && rejected !== null && n - rejected > 0 ? n - rejected : null;
}

// ---- 5. Unusualness (E22) --------------------------------------------------------------------
export interface NoveltyPoint { tau: number; precision: number; n: number }
export function novelty(v: unknown): { chosen: number | null; points: NoveltyPoint[] } | null {
  const points = arr(get(v, "points")).flatMap((p) => {
    const [tau, precision] = [num(get(p, "tau")), num(get(p, "precision"))];
    return tau !== null && precision !== null ? [{ tau, precision, n: num(get(p, "n")) ?? 0 }] : [];
  });
  if (!points.length) return null;
  return { chosen: num(get(v, "chosen_tau")), points: points.sort((a, b) => a.tau - b.tau) };
}

// ---- 6. Does the risk level match what happened? (E21) ---------------------------------------
export type Strength = "none" | "weak" | "moderate";
export interface LevelBox { level: string; n: number; p25: number; median: number; p75: number }
export interface Outcome { key: string; rho: number; lo: number; hi: number; n: number; strength: Strength; boxes: LevelBox[] }

/** The plain verdict from the numbers (B05 §7.6): "no clear" when the 95 % interval crosses 0,
 * "weak" below |ρ| 0.3, "moderate" otherwise. Never stronger, whatever ρ is. */
export function strength(rho: number, lo: number, hi: number): Strength {
  if (lo <= 0 && hi >= 0) return "none";
  return Math.abs(rho) < 0.3 ? "weak" : "moderate";
}

export function outcomes(v: unknown): Outcome[] {
  return arr(get(v, "outcomes")).flatMap((o) => {
    const rho = num(get(o, "rho"));
    const ci = pair(get(o, "ci95"));
    if (rho === null || !ci) return [];
    const boxes = arr(get(o, "by_level")).flatMap((b) => {
      const [p25, median, p75] = [num(get(b, "p25")), num(get(b, "median")), num(get(b, "p75"))];
      return p25 !== null && median !== null && p75 !== null
        ? [{ level: String(get(b, "level") ?? "?"), n: num(get(b, "n")) ?? 0, p25, median, p75 }]
        : [];
    });
    return [{ key: String(get(o, "key") ?? "outcome"), rho, lo: ci[0], hi: ci[1], n: num(get(o, "n")) ?? 0, strength: strength(rho, ci[0], ci[1]), boxes }];
  });
}

// ---- 7. Speed and cost (E23, E24) ------------------------------------------------------------
export interface StageTime { stage: string; p50: number; p95: number }
export interface SpeedCost { stages: StageTime[]; nDocs: number; perPage: number | null; inrMean: number | null; inrMax: number | null; freeShare: number | null }
export function speedCost(latency: unknown, cost: unknown): SpeedCost | null {
  const stages = arr(get(latency, "stages")).flatMap((s) => {
    const [p50, p95] = [num(get(s, "p50_s")), num(get(s, "p95_s"))];
    return p50 !== null && p95 !== null ? [{ stage: String(get(s, "stage") ?? "?"), p50, p95 }] : [];
  });
  const inrMean = num(get(cost, "inr_per_upload_mean"));
  if (!stages.length && inrMean === null) return null;
  return {
    stages,
    nDocs: num(get(latency, "n_docs")) ?? 0,
    perPage: num(get(latency, "s_per_page")),
    inrMean,
    inrMax: num(get(cost, "inr_per_upload_max")),
    freeShare: num(get(cost, "free_share")),
  };
}
