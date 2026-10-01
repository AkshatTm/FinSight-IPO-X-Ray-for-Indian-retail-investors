// MOCK chat streams (development and component tests only). Seven scenarios chosen by keyword:
// normal, scale trick, abstain, advice, forecast, privacy, error. Event order follows docs/06.
// Demo mode never uses these: it replays streams recorded from the real backend.
import type { Schemas } from "@/lib/api/client";
import type { ChatEvent } from "@/lib/sse";

type Money = Schemas["Money"];
export interface Step {
  delay: number;
  ev: ChatEvent;
}

const money = (inr: string, raw: string): Money => ({ kind: "money", value_inr: inr, currency: "INR", raw, scale_word: null, precision: 2 });
const stage = (name: Schemas["StageEvent"]["name"], status: "start" | "end", ms: number | null = null): ChatEvent => ({ event: "stage", data: { name, status, ms } });

const PASSAGE: Schemas["RetrievedPassage"] = {
  n: 1, id: "p-objects", doc: "rhp", page_start: 120, page_end: 120, section: "objects_of_the_offer",
  snippet: "Objects of the Offer. Capital expenditure (₹ in million) 20,000.00. Product development 6,000.00. General corporate purposes [●]. The Fresh Issue is for up to ₹26,260 million.",
  bm25_rank: 2, dense_rank: 1, fused_rank: 1, rerank_score: 0.91,
};
const DROPPED: Schemas["RetrievedPassage"] = { ...PASSAGE, n: 4, id: "p-risk", page_start: 44, page_end: 44, section: "risk_factors", snippet: "Risk factors. We may not utilise the proceeds as planned.", bm25_rank: 9, dense_rank: 7, fused_rank: 8, rerank_score: 0.12 };

const FACTS: Schemas["FactSummary"][] = [
  { field_id: "total_issue_size", label_en: "Total issue size", label_hi: "कुल इश्यू का आकार", display: "₹2,981.00 crore", doc: "rhp", page: 3 },
  { field_id: "fresh_issue_size", label_en: "Fresh issue", label_hi: "फ्रेश इश्यू", display: "₹2,626.00 crore", doc: "rhp", page: 3 },
  { field_id: "ofs_shares", label_en: "Offer for sale (shares)", label_hi: "ओएफएस (शेयर)", display: "1,10,51,746 shares", doc: "rhp", page: 3 },
  { field_id: "face_value", label_en: "Face value", label_hi: "फेस वैल्यू", display: "₹1", doc: "rhp", page: 1 },
];

function frame(parts: ChatEvent[], gap = 140): Step[] {
  return parts.map((ev) => ({ delay: gap, ev }));
}

function tokens(text: string): ChatEvent[] {
  return (text.match(/\S+\s*/g) ?? []).map((t) => ({ event: "token", data: { text: t } }) as ChatEvent);
}

function numberVerdict(text: string, needle: string, index: number, value: Money, status: Schemas["VerdictEvent"]["status"], evValue: Money, reason_code: Schemas["VerdictEvent"]["reason_code"], reason: string): ChatEvent {
  const s = text.indexOf(needle);
  return {
    event: "verdict",
    data: {
      index, answer_char_span: [s, s + needle.length], answer_value: value, status, reason_code, reason,
      evidence: { passage_id: PASSAGE.id, doc: "rhp", page: 120, char_span: [30, 60], bbox: [72, 410, 301, 423], value: evValue },
    },
  };
}

function answerFlow(text: string, citeAt: string, verdicts: ChatEvent[], score: number): Step[] {
  const c = text.indexOf(citeAt);
  return [
    ...frame([stage("guard", "start"), stage("guard", "end", 3), stage("retrieving", "start")], 200),
    ...frame([{ event: "retrieval", data: { passages: [PASSAGE], dropped: [DROPPED] } }, stage("retrieving", "end", 410), stage("generating", "start")], 500),
    ...tokens(text).map((ev) => ({ delay: 60, ev })),
    ...frame([{ event: "answer", data: { text, citations: [{ n: 1, char_start: c, char_end: c + citeAt.length }] } }, stage("generating", "end", 5200), stage("verifying", "start")], 200),
    ...verdicts.map((ev) => ({ delay: 350, ev })),
    ...frame([
      stage("verifying", "end", 40), stage("done", "end"),
      { event: "final", data: { trace_id: "mock-trace-1", score, n_numbers: verdicts.length, timings_ms: { guard: 3, retrieving: 410, generating: 5200, verifying: 40 } } },
    ], 120),
  ];
}

export function scenario(question: string, language: "en" | "hi"): Step[] {
  const q = question.toLowerCase();
  const hi = language === "hi";

  if (/trigger error/.test(q)) {
    return [...frame([stage("guard", "start")], 150), { delay: 300, ev: { event: "error", data: { code: "llm_unavailable", message: "The answer model isn't running." } } }];
  }
  if (/address|phone|e-?mail|contact|पता|फोन/.test(q)) {
    return frame([stage("guard", "start"), { event: "guard", data: { blocked: true, reason: "privacy", facts: [] } }, stage("guard", "end", 2), { event: "final", data: { trace_id: "mock-trace-privacy", score: null, n_numbers: 0, timings_ms: { guard: 2 } } }]);
  }
  if (/will .*(price|profit|list|go up|rise)|predict|forecast|target|मुनाफ़ा|कीमत बढ़/.test(q)) {
    return frame([stage("guard", "start"), { event: "guard", data: { blocked: true, reason: "forecast", facts: [] } }, stage("guard", "end", 2), { event: "final", data: { trace_id: "mock-trace-forecast", score: null, n_numbers: 0, timings_ms: { guard: 2 } } }]);
  }
  if (/should i|apply|invest|buy|worth|आवेदन|निवेश/.test(q)) {
    return frame([stage("guard", "start"), { event: "guard", data: { blocked: true, reason: "advice_intent", facts: FACTS } }, stage("guard", "end", 2), { event: "final", data: { trace_id: "mock-trace-advice", score: null, n_numbers: 0, timings_ms: { guard: 2 } } }]);
  }
  if (/favou?rite|colou?r|ceo's|weather/.test(q)) {
    return [
      ...frame([stage("guard", "start"), stage("guard", "end", 3), stage("retrieving", "start")], 200),
      ...frame([{ event: "retrieval", data: { passages: [PASSAGE], dropped: [DROPPED] } }, stage("retrieving", "end", 380), { event: "abstain", data: { reason: "low_retrieval_score", closest_passage: PASSAGE } }, stage("done", "end"), { event: "final", data: { trace_id: "mock-trace-abstain", score: null, n_numbers: 0, timings_ms: { guard: 3, retrieving: 380 } } }], 400),
    ];
  }
  if (/lakh|लाख/.test(q)) {
    const text = hi
      ? "हाँ, फ्रेश इश्यू ₹26,260 लाख है [1]।"
      : "Yes, the fresh issue is ₹26,260 lakh [1].";
    const needle = hi ? "₹26,260 लाख" : "₹26,260 lakh";
    return answerFlow(text, "[1]", [numberVerdict(text, needle, 0, money("2626000000", needle), "contradicted", money("26260000000", "₹26,260 million"), "scale_mismatch", "Wrong unit.")], 0);
  }
  const text = hi
    ? "कंपनी ₹20,000.00 मिलियन पूंजीगत खर्च और ₹6,000.00 मिलियन उत्पाद विकास पर खर्च करने की योजना बना रही है [1]।"
    : "The company plans to spend ₹20,000.00 million on capital expenditure and ₹6,000.00 million on product development [1].";
  const a = "₹20,000.00 " + (hi ? "मिलियन" : "million");
  const b = "₹6,000.00 " + (hi ? "मिलियन" : "million");
  return answerFlow(text, "[1]", [
    numberVerdict(text, a, 0, money("20000000000", a), "verified", money("20000000000", "20,000.00"), "verified", "Matches."),
    numberVerdict(text, b, 1, money("6000000000", b), "verified", money("6000000000", "6,000.00"), "verified", "Matches."),
  ], 1);
}

export const speed = () => (process.env.NEXT_PUBLIC_MOCK_FAST === "1" ? 0.05 : 1);
