import type { Schemas } from "@/lib/api/client";
import { formatMoney, type Lang } from "@/lib/format";
import { t as translate, type StringKey } from "@/lib/i18n";
import type { ChatEvent } from "@/lib/sse";
import type { DocKind } from "@/lib/doc";

type S = Schemas;
export type Verdict = S["VerdictEvent"];
export type StageName = S["StageEvent"]["name"];

export interface Turn {
  id: string;
  ipoId: string;
  question: string;
  language: Lang;
  status: "streaming" | "done" | "error";
  stage: { name: StageName; startedAt: number } | null;
  guard: S["GuardEvent"] | null;
  retrieval: S["RetrievalEvent"] | null;
  abstain: S["AbstainEvent"] | null;
  /** Tokens as they stream; replaced by the final `answer` text. */
  streamed: string;
  answer: S["AnswerEvent"] | null;
  verdicts: Verdict[];
  final: S["FinalEvent"] | null;
  error: { code: string; message?: string } | null;
}

export function newTurn(id: string, ipoId: string, question: string, language: Lang): Turn {
  return {
    id, ipoId, question, language,
    status: "streaming", stage: null, guard: null, retrieval: null, abstain: null,
    streamed: "", answer: null, verdicts: [], final: null, error: null,
  };
}

/** Pure reducer: one SSE event in, the next turn state out. */
export function applyEvent(turn: Turn, ev: ChatEvent, now = Date.now()): Turn {
  switch (ev.event) {
    case "stage":
      if (ev.data.name === "done") return { ...turn, stage: null };
      return ev.data.status === "start" ? { ...turn, stage: { name: ev.data.name, startedAt: now } } : turn;
    case "guard":
      return { ...turn, guard: ev.data };
    case "retrieval":
      return { ...turn, retrieval: ev.data };
    case "abstain":
      return { ...turn, abstain: ev.data };
    case "token":
      return { ...turn, streamed: turn.streamed + ev.data.text };
    case "answer":
      return { ...turn, answer: ev.data, streamed: ev.data.text };
    case "verdict": {
      const rest = turn.verdicts.filter((v) => v.index !== ev.data.index);
      return { ...turn, verdicts: [...rest, ev.data].sort((a, b) => a.index - b.index) };
    }
    case "final":
      return { ...turn, final: ev.data, status: "done", stage: null };
    case "error":
      return { ...turn, error: ev.data, status: "error", stage: null };
  }
}

export type GuardKind = "advice" | "forecast" | "privacy";

/** Guard reasons from the backend map onto three cards (spec 13.3). */
export function guardKind(reason: string): GuardKind {
  if (reason === "privacy") return "privacy";
  if (/forecast|predict|price_target|listing/.test(reason)) return "forecast";
  return "advice";
}

export interface Meter {
  n: number;
  v: number;
  u: number;
  c: number;
}

export function meter(verdicts: Verdict[]): Meter {
  const v = verdicts.filter((x) => x.status === "verified").length;
  const c = verdicts.filter((x) => x.status === "contradicted").length;
  return { n: verdicts.length, v, c, u: verdicts.length - v - c };
}

/** Footer wording (spec 13.2). */
export function meterText(verdicts: Verdict[], lang: Lang): string {
  const m = meter(verdicts);
  if (m.n === 0) return translate("meter.none", lang);
  if (m.c > 0) return translate("meter.bad", lang, { c: m.c });
  if (m.u > 0) return translate("meter.some", lang, { v: m.v, n: m.n, u: m.u });
  return translate("meter.all", lang, { n: m.n });
}

export type Segment =
  | { type: "text"; text: string }
  | { type: "number"; text: string; verdict: Verdict }
  | { type: "cite"; text: string; n: number };

/** Split the answer into text, checked numbers and citation markers. Bad or overlapping spans are ignored. */
export function segmentAnswer(text: string, verdicts: Verdict[], citations: S["Citation"][]): Segment[] {
  const marks: { start: number; end: number; seg: Segment }[] = [];
  for (const v of verdicts) {
    const [s, e] = v.answer_char_span;
    if (s >= 0 && e > s && e <= text.length) marks.push({ start: s, end: e, seg: { type: "number", text: text.slice(s, e), verdict: v } });
  }
  for (const c of citations) {
    if (c.char_start >= 0 && c.char_end > c.char_start && c.char_end <= text.length)
      marks.push({ start: c.char_start, end: c.char_end, seg: { type: "cite", text: text.slice(c.char_start, c.char_end), n: c.n } });
  }
  marks.sort((a, b) => a.start - b.start || b.end - a.end);
  const out: Segment[] = [];
  let pos = 0;
  for (const m of marks) {
    if (m.start < pos) continue;
    if (m.start > pos) out.push({ type: "text", text: text.slice(pos, m.start) });
    out.push(m.seg);
    pos = m.end;
  }
  if (pos < text.length) out.push({ type: "text", text: text.slice(pos) });
  return out;
}

const crore = (v: Schemas["Money"] | null | undefined, lang: Lang) =>
  v && v.value_inr != null ? formatMoney(v.value_inr, "crore", lang) : "";

type AnyVal = Verdict["answer_value"];
const raw = (v: AnyVal | null | undefined) => (v && "raw" in v ? v.raw : "");
const money = (v: AnyVal | null | undefined) => (v && v.kind === "money" ? v : null);

/** How many times larger b is than a, as readable text ("100", "10", "1,000", "2.5"). */
export function factorText(a: number, b: number): string {
  if (!(a > 0) || !(b > 0)) return "";
  const f = Math.max(a, b) / Math.min(a, b);
  const r = Math.abs(f - Math.round(f)) < 1e-9 * f ? Math.round(f) : Math.round(f * 10) / 10;
  return r.toLocaleString("en-IN");
}

const DOC_NAME: Record<DocKind, Record<Lang, string>> = {
  rhp: { en: "RHP", hi: "आरएचपी" },
  drhp: { en: "DRHP", hi: "डीआरएचपी" },
  prospectus: { en: "Prospectus", hi: "प्रॉस्पेक्टस" },
};

/** Reason text for the evidence drawer from the section 13.1 templates; API reason as the fallback. */
export function reasonText(v: Verdict, lang: Lang): string {
  const ev = v.evidence;
  const doc = ev ? DOC_NAME[ev.doc][lang] : "";
  const page = ev?.page ?? "";
  const key = `reason.${v.reason_code}` as StringKey;
  switch (v.reason_code) {
    case "verified":
    case "not_found":
    case "placeholder":
      return translate(key, lang, { doc, page });
    case "scale_mismatch": {
      const a = money(v.answer_value);
      const b = money(ev?.value as AnyVal);
      if (!a || !b || a.value_inr == null || b.value_inr == null) return v.reason;
      return translate(key, lang, {
        a: a.raw, a_crore: crore(a, lang), b: b.raw, b_crore: crore(b, lang),
        factor: factorText(Number(a.value_inr), Number(b.value_inr)),
      });
    }
    default:
      return v.reason;
  }
}

export interface ComparisonRow {
  asWritten: [string, string];
  crore: [string, string] | null;
  million: [string, string] | null;
}

/** Side-by-side values for the evidence drawer: as written, in crore, in million. */
export function comparison(v: Verdict, lang: Lang): ComparisonRow {
  const a = money(v.answer_value);
  const b = money(v.evidence?.value as AnyVal);
  const conv = (unit: "crore" | "million"): [string, string] | null =>
    a?.value_inr != null && b?.value_inr != null ? [formatMoney(a.value_inr, unit, lang), formatMoney(b.value_inr, unit, lang)] : null;
  return { asWritten: [raw(v.answer_value), raw(v.evidence?.value as AnyVal)], crore: conv("crore"), million: conv("million") };
}

/** Plain text of an answer with its page references, for the Copy button. */
export function copyText(turn: Turn): string {
  if (!turn.answer) return "";
  const refs = (turn.retrieval?.passages ?? [])
    .filter((p) => turn.answer!.citations.some((c) => c.n === p.n))
    .map((p) => `[${p.n}] ${DOC_NAME[p.doc].en} p.${p.page_start}`);
  return refs.length ? `${turn.answer.text}\n\n${refs.join("\n")}` : turn.answer.text;
}
