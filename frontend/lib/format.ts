// Number and date formatting. Spec: docs/12_FRONTEND_SPEC.md section 15.
// Money arrives as decimal strings in full rupees (Money.value_inr). All arithmetic is on
// decimal strings and BigInt so a document figure is never rounded by floating point.

export type Unit = "crore" | "million" | "lakh" | "full";
export type Lang = "en" | "hi";

const UNIT_WORD_HI: Record<Exclude<Unit, "full">, string> = { crore: "करोड़", million: "मिलियन", lakh: "लाख" };
const UNIT_SHIFT: Record<Exclude<Unit, "full">, number> = { crore: 7, million: 6, lakh: 5 };

const HI_MONTHS = [
  "जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
  "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर",
];
const EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Group an unsigned digit string as 1,23,45,678 (Indian) or 12,345,678 (Western). */
export function groupDigits(digits: string, style: "indian" | "western"): string {
  if (!/^\d+$/.test(digits)) throw new Error(`groupDigits: not digits: ${digits}`);
  const d = digits.replace(/^0+(?=\d)/, "");
  if (style === "western") return d.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  if (d.length <= 3) return d;
  const head = d.slice(0, -3);
  const tail = d.slice(-3);
  return head.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + tail;
}

interface Dec {
  neg: boolean;
  int: string;
  frac: string;
}

function numberToPlain(n: number): string {
  if (!Number.isFinite(n)) throw new Error("numberToPlain: not finite");
  const s = n.toString();
  if (!s.includes("e")) return s;
  return BigInt(Math.round(n)).toString();
}

function parseDecimal(input: string | number | bigint): Dec {
  let s = typeof input === "number" ? numberToPlain(input) : String(input).trim();
  s = s.replace(/,/g, "");
  const m = /^(-)?(\d+)(?:\.(\d+))?$/.exec(s);
  if (!m) throw new Error(`parseDecimal: not a decimal: ${String(input)}`);
  return { neg: m[1] === "-", int: m[2], frac: m[3] ?? "" };
}

/** Move the decimal point `places` to the left and round half up to `dp` decimal places. */
function shiftAndRound(d: Dec, places: number, dp: number): Dec {
  const digits = d.int + d.frac;
  const pointAt = d.int.length - places; // index of the decimal point inside `digits`
  let intPart: string;
  let fracPart: string;
  if (pointAt <= 0) {
    intPart = "0";
    fracPart = "0".repeat(-pointAt) + digits;
  } else if (pointAt >= digits.length) {
    intPart = digits + "0".repeat(pointAt - digits.length);
    fracPart = "";
  } else {
    intPart = digits.slice(0, pointAt);
    fracPart = digits.slice(pointAt);
  }
  fracPart = fracPart.padEnd(dp + 1, "0");
  const keep = BigInt(intPart + fracPart.slice(0, dp));
  const roundUp = fracPart.charCodeAt(dp) - 48 >= 5;
  const scaled = (roundUp ? keep + BigInt(1) : keep).toString().padStart(dp + 1, "0");
  const i = dp === 0 ? scaled : scaled.slice(0, -dp);
  const f = dp === 0 ? "" : scaled.slice(-dp);
  return { neg: d.neg, int: i.replace(/^0+(?=\d)/, ""), frac: f };
}

export function formatMoney(valueInr: string | number, unit: Unit, lang: Lang = "en"): string {
  const d = parseDecimal(valueInr);
  const sign = d.neg ? "-" : "";
  if (unit === "full") {
    const hasFrac = /[1-9]/.test(d.frac);
    const r = shiftAndRound(d, 0, hasFrac ? 2 : 0);
    return `${sign}₹${groupDigits(r.int, "indian")}${hasFrac ? "." + r.frac : ""}`;
  }
  const r = shiftAndRound(d, UNIT_SHIFT[unit], 2);
  const style = unit === "million" ? "western" : "indian";
  return `${sign}₹${groupDigits(r.int, style)}.${r.frac} ${lang === "hi" ? UNIT_WORD_HI[unit] : unit}`;
}

/** Rupees per share (face value, price). No unit word; keeps the printed precision. */
export function formatRupee(value: string | number): string {
  const d = parseDecimal(value);
  const frac = d.frac.replace(/0+$/, "");
  return `${d.neg ? "-" : ""}₹${groupDigits(d.int, "indian")}${frac ? "." + frac : ""}`;
}

export function formatShares(
  count: string | number,
  mode: "indian" | "as-written",
  lang: Lang = "en",
): string {
  const d = parseDecimal(count);
  const word = lang === "hi" ? "शेयर" : "shares";
  return `${groupDigits(d.int, mode === "as-written" ? "western" : "indian")} ${word}`;
}

/** One decimal place, half up: 64 -> "64.0%". */
export function formatPercent(value: number): string {
  const d = parseDecimal(value);
  const r = shiftAndRound(d, 0, 1);
  return `${d.neg ? "-" : ""}${r.int}.${r.frac}%`;
}

/** ISO date (YYYY-MM-DD...) to "12 Nov 2025" / "12 नवंबर 2025". No timezone shifts. */
export function formatDate(iso: string, lang: Lang = "en"): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) throw new Error(`formatDate: not an ISO date: ${iso}`);
  const month = Number(m[2]);
  if (month < 1 || month > 12) throw new Error(`formatDate: bad month: ${iso}`);
  const name = (lang === "hi" ? HI_MONTHS : EN_MONTHS)[month - 1];
  return `${Number(m[3])} ${name} ${m[1]}`;
}

/** "Nov 2025" / "नवंबर 2025" for the Library "Listed" column. */
export function formatMonthYear(iso: string, lang: Lang = "en"): string {
  return formatDate(iso, lang).split(" ").slice(1).join(" ");
}

export function fractionPercent(part: string | number, whole: string | number): number | null {
  const p = Number(part);
  const w = Number(whole);
  if (!Number.isFinite(p) || !Number.isFinite(w) || w <= 0) return null;
  return (p / w) * 100;
}
