// Field display rules: docs/12_FRONTEND_SPEC.md section 12 (labels, tooltips, placeholder and
// "not in document" texts). Hindi tooltips were not in the spec: builder drafts, listed in
// docs/AKSHAT_TODO.md under "new copy to review".
import type { Lang } from "@/lib/format";

type Pair = { en: string; hi: string };

export interface FieldContent {
  label: Pair;
  tip: Pair;
  /** Shown when the RHP leaves the value blank and the prospectus has none. */
  placeholder?: Pair;
  /** Shown when the field does not exist in the document (e.g. no fresh issue). */
  notInDocument?: Pair;
}

export const FIELD_CONTENT: Record<string, FieldContent> = {
  total_issue_size: {
    label: { en: "Total issue size", hi: "कुल इश्यू का आकार" },
    tip: { en: "The total value of all shares offered in the IPO.", hi: "आईपीओ में पेश किए गए सभी शेयरों का कुल मूल्य।" },
    placeholder: { en: "Set when the final price is fixed", hi: "अंतिम कीमत तय होने पर पता चलेगा" },
  },
  fresh_issue_size: {
    label: { en: "Fresh issue", hi: "फ्रेश इश्यू" },
    tip: { en: "New shares created by the company. This money goes to the company.", hi: "कंपनी द्वारा बनाए गए नए शेयर। यह पैसा कंपनी को मिलता है।" },
    placeholder: { en: "Amount blank in the RHP", hi: "आरएचपी में रकम खाली है" },
    notInDocument: { en: "None. This IPO has no fresh issue.", hi: "कोई नहीं। इस आईपीओ में फ्रेश इश्यू नहीं है।" },
  },
  ofs_shares: {
    label: { en: "Offer for sale (shares)", hi: "ओएफएस (शेयर)" },
    tip: { en: "Existing shares being sold by current owners.", hi: "मौजूदा मालिकों द्वारा बेचे जा रहे शेयर।" },
    placeholder: { en: "Number of shares blank in the RHP", hi: "शेयरों की संख्या आरएचपी में खाली है" },
  },
  ofs_amount: {
    label: { en: "Offer for sale (amount)", hi: "ओएफएस (रकम)" },
    tip: { en: "Money from the offer for sale. It goes to the sellers, not the company.", hi: "ओएफएस से मिलने वाला पैसा। यह बेचने वालों को जाता है, कंपनी को नहीं।" },
    placeholder: { en: "Set when the final price is fixed", hi: "अंतिम कीमत तय होने पर पता चलेगा" },
  },
  offer_price: {
    label: { en: "Final offer price", hi: "अंतिम ऑफ़र प्राइस" },
    tip: { en: "The price per share set at the end of bidding.", hi: "बोली खत्म होने पर तय हुई प्रति शेयर कीमत।" },
    placeholder: { en: "Not set in the RHP", hi: "आरएचपी में तय नहीं" },
  },
  price_band: {
    label: { en: "Price band", hi: "प्राइस बैंड" },
    tip: { en: "The price range for bids. It's announced separately, so the RHP leaves it blank.", hi: "बोली के लिए कीमतों की सीमा। यह अलग से घोषित होती है, इसलिए आरएचपी में खाली रहती है।" },
    placeholder: { en: "Announced separately, blank in the RHP", hi: "अलग से घोषित, आरएचपी में खाली" },
  },
  face_value: {
    label: { en: "Face value", hi: "फेस वैल्यू" },
    tip: { en: "A fixed accounting value per share. It is not the price you pay.", hi: "प्रति शेयर एक तय लेखा मूल्य। यह वह कीमत नहीं है जो आप देते हैं।" },
  },
  promoters: {
    label: { en: "Promoters", hi: "प्रमोटर" },
    tip: { en: "The people or companies that control the company.", hi: "वे लोग या कंपनियाँ जो कंपनी को नियंत्रित करती हैं।" },
  },
  book_running_lead_managers: {
    label: { en: "Lead managers", hi: "लीड मैनेजर" },
    tip: { en: "Banks that run the IPO process for the company.", hi: "वे बैंक जो कंपनी के लिए आईपीओ की प्रक्रिया संभालते हैं।" },
  },
  registrar: {
    label: { en: "Registrar", hi: "रजिस्ट्रार" },
    tip: { en: "The firm that handles applications and share allotment.", hi: "वह फ़र्म जो आवेदन और शेयर आवंटन संभालती है।" },
  },
  objects_of_offer: {
    label: { en: "Use of the money", hi: "पैसे का उपयोग" },
    tip: { en: "What the company says it will do with the fresh issue money.", hi: "कंपनी के अनुसार फ्रेश इश्यू के पैसे का वह क्या करेगी।" },
    placeholder: { en: "Amount not set yet", hi: "रकम अभी तय नहीं" },
    notInDocument: { en: "Not applicable. The company gets no money from this IPO.", hi: "लागू नहीं। इस आईपीओ से कंपनी को कोई पैसा नहीं मिलता।" },
  },
};

/** Fields whose money value is a price per share, not a total. */
export const PER_SHARE = new Set(["offer_price", "face_value", "price_band"]);

export const GROUPS: { id: "offer" | "people" | "use"; fields: string[] }[] = [
  { id: "offer", fields: ["total_issue_size", "fresh_issue_size", "ofs_shares", "ofs_amount", "offer_price", "price_band", "face_value"] },
  { id: "people", fields: ["promoters", "book_running_lead_managers", "registrar"] },
  { id: "use", fields: ["objects_of_offer"] },
];

export const EXTRACTOR_NAME: Record<string, Pair> = {
  rules: { en: "Rules", hi: "नियम" },
  qa_pretrained: { en: "Pretrained model", hi: "प्रीट्रेंड मॉडल" },
  qa_finetuned: { en: "Our fine-tuned model", hi: "हमारा फ़ाइन-ट्यून मॉडल" },
};

export const CHECK_LABEL: Record<string, Pair> = {
  total_equals_fresh_plus_ofs: { en: "Total = fresh issue + offer for sale", hi: "कुल = फ्रेश इश्यू + ओएफएस" },
};

export const pick = (p: Pair, lang: Lang) => p[lang] || p.en;
