// MOCK X-Ray generator (development only). Every display state of spec section 12 appears for
// at least one IPO: present, placeholder (with prospectus companion), not in document, list, table.
import type { Schemas } from "@/lib/api/client";
import { IPOS } from "./fixtures";

type Field = Schemas["XRayField"];
type Value = NonNullable<Field["value"]>;
type Money = Schemas["Money"];

const money = (inr: string, raw: string, scale: string | null = "crore"): Money => ({
  kind: "money",
  value_inr: inr,
  currency: "INR",
  raw,
  scale_word: scale,
  precision: 2,
});

const base = {
  doc: "rhp" as const,
  printed_page: null,
  bbox: [72, 410, 301, 423] as [number, number, number, number],
  extractor: "rules",
  score: 1,
  verdict: "verified" as const,
  reason_code: "verified" as const,
  reason: "Matches The Offer.",
  companion: null,
  checks: [] as Field["checks"],
  candidates: [] as Field["candidates"],
};

function field(id: string, en: string, hi: string, type: string, value: Value | null, page: number, over: Partial<Field> = {}): Field {
  return { ...base, field_id: id, label_en: en, label_hi: hi, type, value, page, ...over };
}

const placeholder = (raw = "[●]"): Value => ({ kind: "placeholder", raw });

export function buildXray(ipoId: string): Schemas["XRayResponse"] | null {
  const ipo = IPOS.find((i) => i.id === ipoId);
  if (!ipo) return null;
  const hasFresh = !!ipo.fresh_inr && ipo.fresh_inr !== "0";
  const fresh = ipo.fresh_inr ?? "0";
  const ofs = ipo.ofs_inr ?? "0";
  const total = ipo.issue_size_inr ?? "0";
  const crore = (v: string) => `₹ ${(Number(v) / 1e7).toFixed(2)} crore`;
  const isAther = ipoId === "ather-energy-2025";
  const fields: Field[] = [
    field("total_issue_size", "Total issue size", "कुल इश्यू का आकार", "money", ipo.issue_size_inr ? money(total, crore(total)) : placeholder(), 3, {
      extractor: "qa_finetuned",
      score: 0.93,
      verdict: ipo.issue_size_inr ? "verified" : "unverifiable",
      reason_code: ipo.issue_size_inr ? "verified" : "placeholder",
      checks: [{ check: "total_equals_fresh_plus_ofs", status: "verified", reason: "Total equals fresh issue plus offer for sale." }],
      candidates: [
        { extractor: "rules", doc: "rhp", raw: crore(total), value: money(total, crore(total)), page: 3, score: 1, gold_match: true },
        { extractor: "qa_pretrained", doc: "rhp", raw: crore(total), value: money(total, crore(total)), page: 3, score: 0.71, gold_match: true },
        { extractor: "qa_finetuned", doc: "rhp", raw: crore(total), value: money(total, crore(total)), page: 3, score: 0.93, gold_match: true },
      ],
    }),
    hasFresh
      ? field("fresh_issue_size", "Fresh issue", "फ्रेश इश्यू", "money", money(isAther ? "26260000000" : fresh, isAther ? "₹26,260 million" : crore(fresh), isAther ? "million" : "crore"), 3, {
          companion: { doc: "prospectus", page: 3, value: money(fresh, crore(fresh)) },
        })
      : field("fresh_issue_size", "Fresh issue", "फ्रेश इश्यू", "money", null, 3, { verdict: "unverifiable", reason_code: "not_in_document", reason: "None. This IPO has no fresh issue." }),
    field("ofs_shares", "Offer for sale (shares)", "ओएफएस (शेयर)", "count", { kind: "count", value: 11051746, raw: "11,051,746", unit: "shares" }, 3),
    field("ofs_amount", "Offer for sale (amount)", "ओएफएस (रकम)", "money", placeholder(), 3, {
      verdict: "unverifiable",
      reason_code: "placeholder",
      companion: { doc: "prospectus", page: 3, value: money(ofs, crore(ofs)) },
    }),
    field("offer_price", "Final offer price", "अंतिम ऑफ़र प्राइस", "money", placeholder(), 1, {
      verdict: "unverifiable",
      reason_code: "placeholder",
      companion: { doc: "prospectus", page: 1, value: money("321", "₹321", null) },
    }),
    field("price_band", "Price band", "प्राइस बैंड", "range", placeholder(), 1, { verdict: "unverifiable", reason_code: "placeholder" }),
    field("face_value", "Face value", "फेस वैल्यू", "money", money("1", "₹1", null), 1),
    field("promoters", "Promoters", "प्रमोटर", "list", { kind: "list", items: ["Promoter One", "Promoter Two", "Promoter Three", "Promoter Four"] }, 2),
    field("book_running_lead_managers", "Lead managers", "लीड मैनेजर", "list", { kind: "list", items: ["Bank A", "Bank B", "Bank C"] }, 2),
    field("registrar", "Registrar", "रजिस्ट्रार", "text", { kind: "text", text: "Registrar Services Limited" }, 2),
    hasFresh
      ? field("objects_of_offer", "Use of the money", "पैसे का उपयोग", "table", {
          kind: "table",
          columns: ["Object", "Amount (₹ million)"],
          rows: [["Capital expenditure", "20,000.00"], ["Product development", "6,000.00"], ["General corporate purposes", "[●]"]],
        }, 120)
      : field("objects_of_offer", "Use of the money", "पैसे का उपयोग", "table", null, 120, { verdict: "unverifiable", reason_code: "not_in_document" }),
  ];
  const f = Number(fresh);
  const t = Number(total);
  return {
    ipo_id: ipoId,
    company: ipo.company,
    built_at: "2026-10-01T00:00:00Z",
    fields,
    derived: t > 0 ? { fresh_share_pct: ((f / t) * 100).toFixed(2), ofs_share_pct: (((t - f) / t) * 100).toFixed(2) } : {},
  };
}

export const SUGGESTED: Schemas["SuggestedQuestion"][] = [
  { text: "How much money is the company raising?", language: "en", kind: "normal" },
  { text: "What will the money be used for?", language: "en", kind: "normal" },
  { text: "Is the fresh issue ₹800 lakh?", language: "en", kind: "trick" },
  { text: "प्रमोटर कौन हैं?", language: "hi", kind: "normal" },
  { text: "Should I apply for this IPO?", language: "en", kind: "advice" },
];
