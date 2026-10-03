import type { Schemas } from "@/lib/api/client";
import { PER_SHARE } from "@/lib/content/fields";
import { formatMoney, formatPercent, formatRupee, formatShares, type Lang, type Unit } from "@/lib/format";

export type XField = Schemas["XRayField"];
export type XValue = NonNullable<XField["value"]>;

export interface Resolved {
  /** The value to show: the RHP value, or the Prospectus value when the RHP leaves it blank. */
  value: XValue | null;
  doc: XField["doc"];
  page: number;
  /** True when the RHP has `[●]` and the value comes from the final prospectus. */
  filledInProspectus: boolean;
  /** True when the RHP value is blank and no prospectus value exists. */
  blank: boolean;
  /** True when the field is not in the document at all (e.g. no fresh issue). */
  notInDocument: boolean;
  /** Where the shown value sits on `doc`'s page: the field's box, or the companion's. */
  bbox: [number, number, number, number] | null;
}

/** Spec section 12: placeholder rows prefer the prospectus value, with a note. */
export function resolveField(f: XField): Resolved {
  const notInDocument = f.reason_code === "not_in_document" || (f.value == null && f.reason_code !== "placeholder");
  if (f.value?.kind === "placeholder") {
    if (f.companion?.value && f.companion.value.kind !== "placeholder") {
      return { value: f.companion.value, doc: f.companion.doc, page: f.companion.page, filledInProspectus: true, blank: false, notInDocument: false, bbox: f.companion.bbox ?? null };
    }
    return { value: f.value, doc: f.doc, page: f.page, filledInProspectus: false, blank: true, notInDocument: false, bbox: f.bbox ?? null };
  }
  return { value: f.value ?? null, doc: f.doc, page: f.page, filledInProspectus: false, blank: false, notInDocument, bbox: f.bbox ?? null };
}

export const fieldById = (fields: XField[], id: string) => fields.find((f) => f.field_id === id);

// ---- display helpers (spec section 12 and 7.3) -------------------------------------------


/** One-line text for a scalar value; lists and tables are rendered by their own components. */
export function scalarText(
  fieldId: string,
  v: XValue,
  unit: Unit,
  lang: Lang,
  perShareWord: string,
): string | null {
  switch (v.kind) {
    case "money":
      if (v.value_inr == null) return v.raw;
      return PER_SHARE.has(fieldId) ? formatRupee(v.value_inr) : formatMoney(v.value_inr, unit, lang);
    case "count":
      return fieldId === "ofs_shares" ? formatShares(v.value, "indian", lang) : String(v.value);
    case "percent":
      return formatPercent(Number(v.value));
    case "range": {
      if (v.low.value_inr == null || v.high.value_inr == null) return v.raw;
      return `${formatRupee(v.low.value_inr)} – ${formatRupee(v.high.value_inr)} ${perShareWord}`;
    }
    case "text":
      return v.text;
    default:
      return null;
  }
}

/** Per-share wording is added for single prices; ranges carry it already. */
export const needsPerShare = (fieldId: string, v: XValue) => PER_SHARE.has(fieldId) && v.kind === "money" && v.value_inr != null;

type Word = Schemas["PageWord"];

/**
 * The sentence-line around a bbox, rebuilt from page words (the API has no sentence field).
 * Words on the same line (vertical centre inside the box, with a small tolerance) are joined in
 * reading order; those inside the box horizontally are marked as the value.
 */
export function sentenceAround(
  words: Word[],
  bbox: [number, number, number, number],
): { text: string; parts: { text: string; hit: boolean }[] } {
  const [x0, y0, x1, y1] = bbox;
  // Tight tolerance: dense pages set lines about one box-height apart, so a looser band pulls in
  // the neighbouring lines and the sentence reads as nonsense.
  const mid = (y0 + y1) / 2;
  const tol = (y1 - y0) * 0.35;
  const line = words
    .filter((w) => Math.abs((w.b[1] + w.b[3]) / 2 - mid) <= tol)
    .sort((a, b) => a.b[0] - b.b[0]);
  const all = line.map((w) => {
    const cx = (w.b[0] + w.b[2]) / 2;
    return { text: w.t, hit: cx >= x0 - 1 && cx <= x1 + 1 };
  });
  // At most 10 words each side of the value, so a full-width line stays a short quote.
  const first = all.findIndex((p) => p.hit);
  const last = all.length - 1 - [...all].reverse().findIndex((p) => p.hit);
  const parts = first === -1 ? all.slice(0, 20) : all.slice(Math.max(0, first - 10), last + 11);
  return { text: parts.map((p) => p.text).join(" "), parts };
}

export interface ObjectRow {
  label: string;
  /** Rupees as a decimal string, or null for `[●]` / not parseable. */
  inr: string | null;
  raw: string;
}

const COLUMN_UNIT: [RegExp, number][] = [
  [/crore/i, 7],
  [/million|\bmn\b/i, 6],
  [/lakh|lac/i, 5],
];

/** Objects-of-the-offer table: first column = object, amount column read with its unit header. */
export function parseObjectsTable(t: Extract<XValue, { kind: "table" }>): ObjectRow[] {
  const amountCol = t.columns.length - 1;
  const header = t.columns[amountCol] ?? "";
  const shift = COLUMN_UNIT.find(([re]) => re.test(header))?.[1] ?? null;
  return t.rows.map((r) => {
    const raw = (r[amountCol] ?? "").trim();
    const num = raw.replace(/[,\s₹]/g, "");
    let inr: string | null = null;
    if (shift !== null && /^\d+(\.\d+)?$/.test(num)) {
      const [i, f = ""] = num.split(".");
      const digits = i + f;
      const scaled = BigInt(digits) * BigInt(10) ** BigInt(shift - f.length >= 0 ? shift - f.length : 0);
      inr = f.length > shift ? null : scaled.toString();
    }
    return { label: r[0] ?? "", inr, raw };
  });
}
