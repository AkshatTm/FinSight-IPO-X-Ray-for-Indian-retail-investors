// Reads the free-form Model Lab payloads (`/api/lab/*`, files in eval_results/) defensively: every
// reader returns null when a value is missing, and the page hides that part. Shapes follow
// evaluate/ladder.py, seeded_errors.py, retrieval.json, weaklabel_*.json and asr.json.

type Json = Record<string, unknown>;
const isObj = (v: unknown): v is Json => typeof v === "object" && v !== null && !Array.isArray(v);
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const get = (v: unknown, ...path: string[]): unknown => path.reduce<unknown>((n, k) => (isObj(n) ? n[k] : undefined), v);
const pair = (v: unknown): [number, number] | null =>
  Array.isArray(v) && v.length >= 2 && num(v[0]) !== null && num(v[1]) !== null ? [v[0] as number, v[1] as number] : null;

export const pct = (x: number) => Math.round(x * 100);

// ---- 8.1 and 8.2: the extractor ladder -------------------------------------------------------
export interface Cell {
  nvm: number;
  lo: number;
  hi: number;
  n: number;
  nIpos: number;
}
export interface LadderRow {
  key: string;
  label: string;
  full: Cell;
  body: Cell;
}

const KNOWN_RUNGS = ["rules", "qa_pretrained", "qa_finetuned"];

function cell(v: unknown): Cell | null {
  const nvm = num(get(v, "nvm"));
  const ci = pair(get(v, "nvm_ci95"));
  if (nvm === null || !ci) return null;
  return { nvm, lo: ci[0], hi: ci[1], n: num(get(v, "n")) ?? 0, nIpos: num(get(v, "n_ipos")) ?? 0 };
}

export function ladderRows(ladder: unknown): LadderRow[] {
  const split = typeof get(ladder, "headline_split") === "string" ? (get(ladder, "headline_split") as string) : "test";
  const rungs = get(ladder, "ladder");
  if (!isObj(rungs)) return [];
  const keys = [...KNOWN_RUNGS.filter((k) => k in rungs), ...Object.keys(rungs).filter((k) => !KNOWN_RUNGS.includes(k))];
  const rows: LadderRow[] = [];
  for (const key of keys) {
    const full = cell(get(rungs[key], split, "full"));
    const body = cell(get(rungs[key], split, "body_only"));
    if (full && body) rows.push({ key, label: String(get(rungs[key], "label") ?? key), full, body });
  }
  return rows;
}

export function ladderTakeaway(ladder: unknown): { rulesBody: number; ftBody: number; delta: number } | null {
  const rows = ladderRows(ladder);
  const rules = rows.find((r) => r.key === "rules");
  const ft = rows.find((r) => r.key === "qa_finetuned");
  const diff = num(get(ladder, "paired_test", "qa_finetuned_minus_qa_pretrained", "full", "diff"));
  if (!rules || !ft || diff === null) return null;
  return { rulesBody: pct(rules.body.nvm), ftBody: pct(ft.body.nvm), delta: pct(diff) };
}

/** n values and k IPOs behind the headline columns (the larger of full and body-only). */
export function ladderSize(ladder: unknown): { n: number; k: number } | null {
  const rows = ladderRows(ladder);
  if (!rows.length) return null;
  return { n: Math.max(...rows.map((r) => r.full.n)), k: Math.max(...rows.map((r) => r.full.nIpos)) };
}

export interface Example {
  ipo: string;
  doc: string;
  page: number | null;
  read: string;
  checked: string;
  correct: boolean;
}
export interface Heatmap {
  fields: string[];
  rows: { key: string; cells: Record<string, number | null>; examples: Record<string, Example[]> }[];
}

function examples(v: unknown): Example[] {
  if (!Array.isArray(v)) return [];
  return v.flatMap((e): Example[] =>
    isObj(e) && typeof e.read === "string" && typeof e.checked === "string"
      ? [{ ipo: String(e.ipo_id ?? ""), doc: String(e.doc ?? ""), page: num(e.page), read: e.read, checked: e.checked, correct: e.correct === true }]
      : [],
  );
}

export function heatmap(ladder: unknown): Heatmap | null {
  const per = get(ladder, "per_field_test");
  if (!isObj(per)) return null;
  const present = Object.keys(per).filter((k) => isObj(get(per, k, "full")));
  const rungs = [...KNOWN_RUNGS.filter((k) => present.includes(k)), ...present.filter((k) => !KNOWN_RUNGS.includes(k))];
  if (!rungs.length) return null;
  const fields = [...new Set(rungs.flatMap((k) => Object.keys(get(per, k, "full") as Json)))];
  return {
    fields,
    rows: rungs.map((key) => ({
      key,
      cells: Object.fromEntries(fields.map((f) => [f, num(get(per, key, "full", f, "nvm"))])),
      examples: Object.fromEntries(fields.map((f) => [f, examples(get(ladder, "examples_test", key, "full", f))])),
    })),
  };
}

// ---- 8.3: automatic labels -------------------------------------------------------------------
export function weakStats(w: unknown): { examples: number; ipos: number; precision: number; lo: number; hi: number } | null {
  const train = num(get(w, "train", "examples"));
  const dev = num(get(w, "dev", "examples"));
  const ipos = num(get(w, "n_ipos"));
  const precision = num(get(w, "audit", "precision"));
  const ci = pair(get(w, "audit", "wilson_95"));
  if (train === null || ipos === null || precision === null || !ci) return null;
  return { examples: train + (dev ?? 0), ipos, precision: pct(precision), lo: pct(ci[0]), hi: pct(ci[1]) };
}

// ---- 8.4: the verifier -----------------------------------------------------------------------
export interface Rate {
  hits: number;
  n: number;
}
const rate = (v: unknown): Rate | null => {
  const hits = num(get(v, "hits"));
  const n = num(get(v, "n"));
  return hits === null || n === null ? null : { hits, n };
};

export interface VerifierStats {
  caught: Rate;
  falseAlarms: Rate | null;
  unit: Rate | null;
  unitFixed: Rate | null;
  types: { key: string; n: number; ok: number }[];
}

const TYPE_ORDER = ["digit", "scale", "swap_metric", "invented", "rounding_ok", "correct"];

export function verifierStats(v: unknown): VerifierStats | null {
  const caught = rate(get(v, "headline", "detection", "held_out")) ?? rate(get(v, "metrics", "detection"));
  if (!caught) return null;
  const per = get(v, "metrics", "per_type");
  const merged: Record<string, { n: number; ok: number }> = {};
  if (isObj(per)) {
    for (const [k, row] of Object.entries(per)) {
      const n = num(get(row, "n"));
      const ok = num(get(row, "ok"));
      if (n === null || ok === null) continue;
      const key = k.startsWith("scale_") ? "scale" : k;
      merged[key] = { n: (merged[key]?.n ?? 0) + n, ok: (merged[key]?.ok ?? 0) + ok };
    }
  }
  return {
    caught,
    falseAlarms: rate(get(v, "headline", "false_alarm", "held_out")) ?? rate(get(v, "metrics", "false_alarm")),
    unit: rate(get(v, "headline", "scale_mismatch_recall", "held_out")),
    unitFixed: rate(get(v, "headline", "scale_mismatch_recall", "after_one_rule_fix")),
    types: TYPE_ORDER.filter((k) => k in merged).map((key) => ({ key, ...merged[key] })),
  };
}

// ---- 8.5 and 8.7: retrieval and Hindi --------------------------------------------------------
export interface RetrievalRow {
  key: string;
  recall5: number;
  hiRecall5: number | null;
  abstained: string | null;
}

export function retrievalRows(r: unknown): RetrievalRow[] {
  const methods = get(r, "methods");
  if (!isObj(methods)) return [];
  const out: RetrievalRow[] = [];
  for (const key of ["bm25", "dense", "hybrid", "hybrid+rerank"]) {
    const recall5 = num(get(methods, key, "test", "all", "recall@5", "mean"));
    if (recall5 === null) continue;
    const abst = get(methods, key, "abstain", "test_unanswerable_abstained");
    out.push({
      key,
      recall5,
      hiRecall5: num(get(methods, key, "test", "hi", "recall@5", "mean")),
      abstained: typeof abst === "string" ? abst : null,
    });
  }
  return out;
}

export function asrStats(a: unknown): { cer: number; clips: number } | null {
  const models = get(a, "models");
  if (!isObj(models)) return null;
  // The model the full profile uses (ADR-021), else the best one reported.
  const best = num(get(models, "large-v3-turbo", "summary", "mean_cer"));
  const cer = best ?? Math.min(...Object.values(models).map((m) => num(get(m, "summary", "mean_cer")) ?? Infinity));
  const clips = num(get(a, "n_clips"));
  return Number.isFinite(cer) && clips !== null ? { cer: Math.round(cer * 1000) / 10, clips } : null;
}
