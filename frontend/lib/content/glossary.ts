// Glossary: docs/12_FRONTEND_SPEC.md section 14 (short definitions, EN + HI). The spec gives no
// long definitions, so the drawer shows the short one. The backend /api/glossary should serve
// this same list (spec 14); until then this file is the source.
import type { Lang } from "@/lib/format";

interface Entry {
  id: string;
  title: { en: string; hi: string };
  short: { en: string; hi: string };
}

export const GLOSSARY: Entry[] = [
  { id: "ipo", title: { en: "IPO", hi: "आईपीओ" }, short: { en: "When a company sells shares to the public for the first time.", hi: "जब कोई कंपनी पहली बार आम लोगों को शेयर बेचती है।" } },
  { id: "demat", title: { en: "Demat account", hi: "डीमैट खाता" }, short: { en: "An account that holds your shares electronically. You need one to apply in an IPO.", hi: "एक खाता जिसमें आपके शेयर इलेक्ट्रॉनिक रूप में रहते हैं। आईपीओ में आवेदन के लिए यह ज़रूरी है।" } },
  { id: "rhp", title: { en: "RHP (Red Herring Prospectus)", hi: "आरएचपी" }, short: { en: "The offer document filed before the IPO opens. The price and some amounts are left blank.", hi: "आईपीओ खुलने से पहले दाख़िल किया गया ऑफ़र दस्तावेज़। इसमें कीमत और कुछ रकम खाली छोड़ी जाती हैं।" } },
  { id: "prospectus", title: { en: "Prospectus (final)", hi: "फ़ाइनल प्रॉस्पेक्टस" }, short: { en: "The version filed after the price is fixed, with the blanks filled in.", hi: "कीमत तय होने के बाद दाख़िल किया गया संस्करण, जिसमें खाली जगहें भरी होती हैं।" } },
  { id: "drhp", title: { en: "DRHP", hi: "डीआरएचपी" }, short: { en: "The first draft filed with SEBI for review, before the RHP.", hi: "आरएचपी से पहले सेबी को जाँच के लिए भेजा गया पहला मसौदा।" } },
  { id: "sebi", title: { en: "SEBI", hi: "सेबी" }, short: { en: "India's securities market regulator. It sets the rules for IPOs.", hi: "भारत का प्रतिभूति बाज़ार नियामक। यह आईपीओ के नियम तय करता है।" } },
  { id: "fresh_issue", title: { en: "Fresh issue", hi: "फ्रेश इश्यू" }, short: { en: "New shares created by the company. The money goes to the company.", hi: "कंपनी द्वारा बनाए गए नए शेयर। पैसा कंपनी को मिलता है।" } },
  { id: "ofs", title: { en: "Offer for sale (OFS)", hi: "ओएफएस" }, short: { en: "Existing owners selling some of their shares. The money goes to them, not the company.", hi: "मौजूदा मालिक अपने कुछ शेयर बेचते हैं। पैसा उन्हें मिलता है, कंपनी को नहीं।" } },
  { id: "price_band", title: { en: "Price band", hi: "प्राइस बैंड" }, short: { en: "The range of prices within which you can bid.", hi: "कीमतों की वह सीमा जिसके भीतर आप बोली लगा सकते हैं।" } },
  { id: "offer_price", title: { en: "Offer price", hi: "ऑफ़र प्राइस" }, short: { en: "The final price per share, set after bidding closes.", hi: "बोली बंद होने के बाद तय की गई प्रति शेयर अंतिम कीमत।" } },
  { id: "face_value", title: { en: "Face value", hi: "फेस वैल्यू" }, short: { en: "A fixed accounting value per share, like ₹1 or ₹10. It's not the price you pay.", hi: "प्रति शेयर एक तय लेखा मूल्य, जैसे ₹1 या ₹10। यह वह कीमत नहीं है जो आप देते हैं।" } },
  { id: "promoter", title: { en: "Promoter", hi: "प्रमोटर" }, short: { en: "The person or company that controls the company.", hi: "वह व्यक्ति या कंपनी जो कंपनी को नियंत्रित करती है।" } },
  { id: "brlm", title: { en: "Book running lead manager", hi: "बुक रनिंग लीड मैनेजर" }, short: { en: "A bank hired to manage the IPO.", hi: "आईपीओ संभालने के लिए नियुक्त बैंक।" } },
  { id: "registrar", title: { en: "Registrar", hi: "रजिस्ट्रार" }, short: { en: "The firm that processes applications and allots shares.", hi: "वह फ़र्म जो आवेदन संभालती है और शेयर आवंटित करती है।" } },
  { id: "objects", title: { en: "Objects of the offer", hi: "ऑफ़र के उद्देश्य" }, short: { en: "What the company plans to do with the money from the fresh issue.", hi: "फ्रेश इश्यू से मिले पैसे से कंपनी क्या करने वाली है।" } },
  { id: "units", title: { en: "Lakh, crore, million", hi: "लाख, करोड़, मिलियन" }, short: { en: "1 lakh = 1,00,000. 1 crore = 100 lakh. 1 million = 10 lakh. So ₹100 crore = ₹1,000 million.", hi: "1 लाख = 1,00,000। 1 करोड़ = 100 लाख। 1 मिलियन = 10 लाख। यानी ₹100 करोड़ = ₹1,000 मिलियन।" } },
  { id: "blank", title: { en: "[●] (blank)", hi: "[●] (खाली)" }, short: { en: "A blank in the RHP for a value that isn't decided yet, usually the price.", hi: "आरएचपी में किसी ऐसे मान के लिए खाली जगह जो अभी तय नहीं है, आमतौर पर कीमत।" } },
  { id: "gmp", title: { en: "GMP", hi: "जीएमपी" }, short: { en: "“Grey market premium”: unofficial trading talk before listing. It's not in the documents and FinSight doesn't track it.", hi: "“ग्रे मार्केट प्रीमियम”: लिस्टिंग से पहले की अनौपचारिक चर्चा। यह दस्तावेज़ों में नहीं होता और FinSight इसे ट्रैक नहीं करता।" } },
];

export const glossaryEntry = (id: string) => GLOSSARY.find((g) => g.id === id);
export const glossaryText = (id: string, lang: Lang) => {
  const e = glossaryEntry(id);
  return e ? { title: e.title[lang] || e.title.en, short: e.short[lang] || e.short.en } : null;
};

/** X-Ray field -> glossary term, for the dotted underline on fact labels. */
export const FIELD_TERM: Record<string, string> = {
  fresh_issue_size: "fresh_issue",
  ofs_shares: "ofs",
  ofs_amount: "ofs",
  offer_price: "offer_price",
  price_band: "price_band",
  face_value: "face_value",
  promoters: "promoter",
  book_running_lead_managers: "brlm",
  registrar: "registrar",
  objects_of_offer: "objects",
};
