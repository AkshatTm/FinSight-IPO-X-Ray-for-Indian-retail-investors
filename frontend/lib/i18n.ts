// Every UI string, EN + HI. Source: docs/12_FRONTEND_SPEC.md (copy is verbatim; do not reword).
// Strings marked [HI review] in the spec are listed in docs/AKSHAT_TODO.md.
// Page-level copy is added here with the step that builds the page.
// Interpolation: {name}. Numbers stay Western digits in Hindi.

export type Lang = "en" | "hi";
type Entry = { en: string; hi: string };

const d = <T extends Record<string, Entry>>(x: T) => x;

export const STRINGS = d({
  // 3.1 navigation
  "nav.home": { en: "FinSight", hi: "FinSight" },
  "nav.ipos": { en: "IPOs", hi: "आईपीओ" },
  "nav.how": { en: "How it works", hi: "यह कैसे काम करता है" },
  "nav.lab": { en: "Model Lab", hi: "मॉडल लैब" },
  "nav.about": { en: "About", hi: "परिचय" },
  "nav.try": { en: "Try it", hi: "आज़माएँ" },
  "nav.menu": { en: "Menu", hi: "मेनू" },
  "nav.close": { en: "Close", hi: "बंद करें" },
  "nav.theme": { en: "Theme", hi: "थीम" },
  "nav.language": { en: "Language", hi: "भाषा" },
  "nav.skip": { en: "Skip to content", hi: "सीधे सामग्री पर जाएँ" },
  "lang.tooltip": {
    en: "Changes the interface and the language of new answers.",
    hi: "इंटरफ़ेस और नए जवाबों की भाषा बदलता है।",
  },

  // 3.2 health dot
  "health.label": { en: "Server status", hi: "सर्वर की स्थिति" },
  "health.ok": { en: "Everything is running", hi: "सब ठीक चल रहा है" },
  "health.warming": {
    en: "Models are loading. This takes about 20 seconds the first time.",
    hi: "मॉडल लोड हो रहे हैं। पहली बार में लगभग 20 सेकंड लगते हैं।",
  },
  "health.degraded": {
    en: "Running with reduced features. {detail}",
    hi: "कुछ सुविधाएँ अभी सीमित हैं। {detail}",
  },
  "health.unreachable": {
    en: "Can't reach the FinSight server. Demo answers still work.",
    hi: "FinSight सर्वर से संपर्क नहीं हो पा रहा। डेमो उत्तर फिर भी काम करेंगे।",
  },

  // 3.3 footer
  "footer.notAdviceBold": { en: "Not investment advice.", hi: "यह निवेश सलाह नहीं है।" },
  "footer.notAdviceRest": {
    en: "FinSight explains what public IPO documents say. It does not tell you whether to apply.",
    hi: "FinSight बताता है कि सार्वजनिक आईपीओ दस्तावेज़ों में क्या लिखा है। यह नहीं बताता कि आपको आवेदन करना चाहिए या नहीं।",
  },
  "footer.built": {
    en: "Built by Akshat Tomar for CSE472 (Deep Learning for NLP), Lovely Professional University",
    hi: "Akshat Tomar ने CSE472 (Deep Learning for NLP), Lovely Professional University के लिए बनाया",
  },
  "footer.data": { en: "Data: public SEBI filings", hi: "डेटा: सेबी में दाख़िल सार्वजनिक दस्तावेज़" },
  "footer.source": { en: "Source code on GitHub", hi: "GitHub पर सोर्स कोड" },

  // 4 global states
  "banner.coldBold": { en: "Getting ready.", hi: "तैयारी हो रही है।" },
  "banner.coldRest": {
    en: "The models are loading on this computer. Answers will start in about 20 seconds.",
    hi: "मॉडल इस कंप्यूटर पर लोड हो रहे हैं। लगभग 20 सेकंड में उत्तर मिलने लगेंगे।",
  },
  "banner.dismiss": { en: "Dismiss", hi: "हटाएँ" },
  "toast.copied": { en: "Answer copied with page numbers.", hi: "पेज नंबर के साथ उत्तर कॉपी हो गया।" },
  "toast.linkCopied": { en: "Link copied.", hi: "लिंक कॉपी हो गया।" },
  "error.title": { en: "Something went wrong here.", hi: "यहाँ कुछ गड़बड़ हो गई।" },
  "error.retry": { en: "Try again", hi: "फिर से कोशिश करें" },
  "loading": { en: "Loading", hi: "लोड हो रहा है" },
  "glossary.more": { en: "More in the glossary", hi: "शब्दकोश में और देखें" },

  // 2.4 / 7.6 verdict marks
  "verdict.verified": { en: "Matches", hi: "मेल खाता है" },
  "verdict.unverifiable": { en: "Couldn't check", hi: "जाँच नहीं हो सकी" },
  "verdict.contradicted": { en: "Doesn't match", hi: "मेल नहीं खाता" },
  "verdict.placeholder": { en: "Blank in RHP", hi: "RHP में खाली" },
  "evidence.title.verified": { en: "This number matches", hi: "यह आंकड़ा मेल खाता है" },
  "evidence.title.unverifiable": {
    en: "This number couldn't be checked",
    hi: "इस आंकड़े की जाँच नहीं हो सकी",
  },
  "evidence.title.contradicted": { en: "This number doesn't match", hi: "यह आंकड़ा मेल नहीं खाता" },

  // 3 units (7.3.3)
  "unit.crore": { en: "₹ crore", hi: "₹ करोड़" },
  "unit.million": { en: "₹ million", hi: "₹ मिलियन" },
  "unit.lakh": { en: "₹ lakh", hi: "₹ लाख" },
  "unit.full": { en: "₹ (full)", hi: "₹ (पूरा)" },
  "unit.tooltip": {
    en: "Change how amounts are shown. The document's own wording is kept in the source view.",
    hi: "रकम दिखाने का तरीका बदलें। दस्तावेज़ के मूल शब्द सोर्स में वैसे ही रहेंगे।",
  },

  // 7.5.3 stage line
  "stage.guard": { en: "Checking the question", hi: "सवाल जाँच रहे हैं" },
  "stage.retrieving": { en: "Finding the right pages", hi: "सही पन्ने ढूँढ रहे हैं" },
  "stage.generating": { en: "Writing the answer", hi: "जवाब लिख रहे हैं" },
  "stage.verifying": { en: "Checking every number", hi: "हर आंकड़ा जाँच रहे हैं" },

  // 7.5.6 voice
  "voice.idle": { en: "Ask by voice", hi: "आवाज़ से पूछें" },
  "voice.permission": {
    en: "FinSight needs your microphone to hear the question.",
    hi: "सवाल सुनने के लिए FinSight को आपके माइक्रोफ़ोन की ज़रूरत है।",
  },
  "voice.recording": { en: "Listening… tap to stop", hi: "सुन रहे हैं… रोकने के लिए टैप करें" },
  "voice.transcribing": {
    en: "Turning your voice into text. This takes about 10 seconds.",
    hi: "आपकी आवाज़ को टेक्स्ट में बदल रहे हैं। इसमें लगभग 10 सेकंड लगते हैं।",
  },
  "voice.done": {
    en: "Heard in Hindi. Check the text, then press Ask.",
    hi: "हिंदी में सुना गया। टेक्स्ट जाँचें, फिर पूछें दबाएँ।",
  },
  "voice.tooLong": {
    en: "That was longer than 20 seconds. Try a shorter question.",
    hi: "यह 20 सेकंड से लंबा था। छोटा सवाल आज़माएँ।",
  },
  "voice.failed": {
    en: "Couldn't understand the audio. Try again in a quieter place, or type your question.",
    hi: "ऑडियो समझ नहीं आया। किसी शांत जगह से फिर कोशिश करें, या सवाल लिख दें।",
  },
  "voice.blocked": {
    en: "Microphone access is blocked. You can allow it in your browser settings, or type instead.",
    hi: "माइक्रोफ़ोन की अनुमति बंद है। ब्राउज़र सेटिंग में इसे चालू करें, या सवाल लिख दें।",
  },

  // 13.1 verdict reasons
  "reason.verified": {
    en: "This number is in the document, for the same item, on {doc} page {page}.",
    hi: "यह आंकड़ा दस्तावेज़ में, इसी चीज़ के लिए, {doc} के पन्ना {page} पर है।",
  },
  "reason.scale_mismatch": {
    en: "Wrong unit. The answer says {a} ({a_crore}). The document says {b} ({b_crore}). That's {factor} times different.",
    hi: "इकाई गलत है। जवाब में {a} ({a_crore}) है। दस्तावेज़ में {b} ({b_crore}) है। यह {factor} गुना का अंतर है।",
  },
  "reason.wrong_value": {
    en: "Different number. For {metric}, the document says {b} on {doc} page {page}.",
    hi: "आंकड़ा अलग है। {metric} के लिए दस्तावेज़ में {doc} के पन्ना {page} पर {b} लिखा है।",
  },
  "reason.wrong_metric": {
    en: "This number belongs to {other_metric}, not {metric}.",
    hi: "यह आंकड़ा {metric} का नहीं, {other_metric} का है।",
  },
  "reason.not_found": {
    en: "This number doesn't appear in the pages used for this answer. It may still be correct, but FinSight couldn't confirm it.",
    hi: "यह आंकड़ा इस जवाब के लिए इस्तेमाल हुए पन्नों में नहीं है। यह सही हो सकता है, पर FinSight इसकी पुष्टि नहीं कर सका।",
  },
  "reason.placeholder": {
    en: "The RHP leaves this blank ([●]). It's filled in later, in the final prospectus.",
    hi: "आरएचपी में यह खाली ([●]) है। यह बाद में फ़ाइनल प्रॉस्पेक्टस में भरा जाता है।",
  },

  // 13.2 faithfulness meter
  "meter.none": {
    en: "No numbers to check in this answer.",
    hi: "इस जवाब में जाँचने लायक कोई आंकड़ा नहीं है।",
  },
  "meter.all": { en: "{n} of {n} numbers match the document", hi: "{n} में से {n} आंकड़े दस्तावेज़ से मेल खाते हैं" },
  "meter.some": {
    en: "{v} of {n} numbers match. {u} couldn't be checked.",
    hi: "{n} में से {v} आंकड़े मेल खाते हैं। {u} की जाँच नहीं हो सकी।",
  },
  "meter.bad": {
    en: "{c} number(s) don't match the document. Check the marked ones.",
    hi: "{c} आंकड़े दस्तावेज़ से मेल नहीं खाते। निशान लगे आंकड़े देखें।",
  },

  // 13.3 guard cards
  "guard.advice.title": {
    en: "I can't tell you whether to invest.",
    hi: "मैं यह नहीं बता सकता कि निवेश करें या नहीं।",
  },
  "guard.advice.body": {
    en: "In India, only advisers registered with SEBI can give investment advice. Here's what the documents say, so you can decide for yourself or ask an adviser.",
    hi: "भारत में केवल सेबी में पंजीकृत सलाहकार ही निवेश सलाह दे सकते हैं। दस्तावेज़ों में यह लिखा है, ताकि आप ख़ुद तय कर सकें या किसी सलाहकार से पूछ सकें।",
  },
  "guard.advice.sebi": { en: "What is SEBI?", hi: "सेबी क्या है?" },
  "guard.forecast.title": {
    en: "I can't predict prices or profits.",
    hi: "मैं कीमत या मुनाफ़े का अनुमान नहीं लगा सकता।",
  },
  "guard.forecast.body": {
    en: "The documents describe the past and the plan, not the future. I can show what they say about past results or how the money will be used.",
    hi: "दस्तावेज़ बीते समय और योजना के बारे में बताते हैं, भविष्य के बारे में नहीं। मैं दिखा सकता हूँ कि पिछले नतीजों या पैसे के उपयोग के बारे में उनमें क्या लिखा है।",
  },
  "guard.forecast.chipMoney": { en: "What will the money be used for?", hi: "पैसा किस काम में लगेगा?" },
  "guard.forecast.chipPast": { en: "Past revenue and profit", hi: "पिछली आमदनी और मुनाफ़ा" },
  "guard.privacy.title": { en: "I don't share personal details.", hi: "मैं निजी जानकारी नहीं देता।" },
  "guard.privacy.body": {
    en: "Offer documents list home addresses and contact details of some people. FinSight doesn't show them, even though they're public. I can tell you who the promoters and directors are and their roles.",
    hi: "ऑफ़र दस्तावेज़ों में कुछ लोगों के घर के पते और संपर्क जानकारी होती है। सार्वजनिक होने के बावजूद FinSight इन्हें नहीं दिखाता। मैं बता सकता हूँ कि प्रमोटर और डायरेक्टर कौन हैं और उनकी भूमिका क्या है।",
  },

  // 13.4 abstain
  "abstain.title": {
    en: "I couldn't find this in the documents.",
    hi: "यह मुझे दस्तावेज़ों में नहीं मिला।",
  },
  "abstain.body": {
    en: "Rather than guess, FinSight only answers from the pages. The closest page it found is below.",
    hi: "अंदाज़ा लगाने के बजाय FinSight केवल पन्नों से जवाब देता है। सबसे क़रीबी पन्ना नीचे है।",
  },
  "abstain.tryDifferent": { en: "Try asking it differently", hi: "इसे दूसरे तरीके से पूछें" },
  "common.showInDocument": { en: "Show in document", hi: "दस्तावेज़ में दिखाएँ" },

  // 13.5 API error codes
  "err.llm_unavailable": {
    en: "The answer model isn't running right now. Try again in a minute. Demo questions still work.",
    hi: "जवाब देने वाला मॉडल अभी नहीं चल रहा। एक मिनट बाद फिर कोशिश करें। डेमो सवाल फिर भी काम करेंगे।",
  },
  "err.models_warming_up": {
    en: "The models are still loading. This takes about 20 seconds the first time.",
    hi: "मॉडल अभी लोड हो रहे हैं। पहली बार में लगभग 20 सेकंड लगते हैं।",
  },
  "err.ipo_not_found": { en: "We couldn't find that IPO.", hi: "वह आईपीओ नहीं मिला।" },
  "err.page_out_of_range": { en: "That page isn't in this document.", hi: "वह पन्ना इस दस्तावेज़ में नहीं है।" },
  "err.rate_limited": {
    en: "Too many questions at once. Wait a few seconds.",
    hi: "एक साथ बहुत सारे सवाल। कुछ सेकंड रुकें।",
  },
  "err.validation_error": {
    en: "Something about that question didn't work. Try rephrasing it.",
    hi: "उस सवाल में कुछ गड़बड़ हुई। इसे दूसरे शब्दों में पूछें।",
  },
  "err.internal_error": {
    en: "Something went wrong on our side. Try again.",
    hi: "हमारी तरफ़ से कुछ गड़बड़ हुई। फिर से कोशिश करें।",
  },
  "err.network": {
    en: "Can't reach the FinSight server. Check that it's running.",
    hi: "FinSight सर्वर से संपर्क नहीं हो पा रहा। जाँचें कि यह चल रहा है।",
  },

  // 7.9 tour
  "tour.1": {
    en: "These are the key facts from the offer document. Click one.",
    hi: "ये ऑफ़र दस्तावेज़ के मुख्य तथ्य हैं। किसी एक पर क्लिक करें।",
  },
  "tour.2": {
    en: "This is the real page. The box shows exactly where the fact came from.",
    hi: "यह असली पन्ना है। बॉक्स दिखाता है कि तथ्य ठीक कहाँ से आया।",
  },
  "tour.3": {
    en: "Ask a question. Every number in the answer gets a mark.",
    hi: "सवाल पूछें। जवाब के हर आंकड़े पर निशान लगेगा।",
  },
  "tour.next": { en: "Next", hi: "आगे" },
  "tour.done": { en: "Got it", hi: "समझ गया" },
  "tour.skip": { en: "Skip tour", hi: "टूर छोड़ें" },

  // 11 error pages
  "404.title": { en: "This page doesn't exist.", hi: "यह पन्ना मौजूद नहीं है।" },
  "404.body": { en: "The link may be old. Try the IPO list.", hi: "लिंक पुराना हो सकता है। आईपीओ सूची देखें।" },
  "404.button": { en: "Browse IPOs", hi: "आईपीओ देखें" },
  "500.title": { en: "Something broke on our side.", hi: "हमारी तरफ़ से कुछ गड़बड़ हो गई।" },
  "500.body": {
    en: "Reloading usually fixes it. If not, the demo pages still work.",
    hi: "पेज रीलोड करने से अक्सर ठीक हो जाता है। नहीं तो डेमो पेज फिर भी काम करेंगे।",
  },
  "500.button": { en: "Reload", hi: "रीलोड करें" },

  // 6 IPO Library
  "lib.title": { en: "IPOs", hi: "आईपीओ" },
  "lib.sub": {
    en: "{n} recent IPOs from the NSE and BSE. Pick one to see its facts, the original pages, and ask questions.",
    hi: "एनएसई और बीएसई के {n} हाल के आईपीओ। किसी एक को चुनें, उसके तथ्य और मूल पन्ने देखें, और सवाल पूछें।",
  },
  "lib.search": { en: "Search by company or sector", hi: "कंपनी या सेक्टर से खोजें" },
  "lib.sort.newest": { en: "Newest first", hi: "सबसे नए पहले" },
  "lib.sort.largest": { en: "Largest issue first", hi: "सबसे बड़ा इश्यू पहले" },
  "lib.sort.az": { en: "A to Z", hi: "A से Z" },
  "lib.sort.label": { en: "Sort", hi: "क्रम" },
  "lib.filter.all": { en: "All", hi: "सभी" },
  "lib.filter.fresh": { en: "Has fresh issue", hi: "फ्रेश इश्यू वाले" },
  "lib.filter.ofs": { en: "Only offer for sale", hi: "केवल ओएफएस" },
  "lib.listed": { en: "Listed {month}", hi: "सूचीबद्ध {month}" },
  "lib.issueSize": { en: "Issue size", hi: "इश्यू का आकार" },
  "lib.pages": { en: "{n} pages", hi: "{n} पन्ने" },
  "lib.fresh": { en: "Fresh {x}", hi: "फ्रेश {x}" },
  "lib.ofsPct": { en: "OFS {y}", hi: "ओएफएस {y}" },
  "lib.onlyOfs": { en: "Only offer for sale", hi: "केवल बिक्री प्रस्ताव (ओएफएस)" },
  "lib.offerPrice": { en: "Offer price", hi: "ऑफ़र प्राइस" },
  "lib.faceValue": { en: "Face value", hi: "फेस वैल्यू" },
  "lib.managers": { en: "Lead managers", hi: "लीड मैनेजर" },
  "lib.empty": {
    en: "No IPO matches “{query}”. Try a company name like Lenskart.",
    hi: "“{query}” से कोई आईपीओ नहीं मिला। Lenskart जैसा कंपनी का नाम आज़माएँ।",
  },
  "lib.clear": { en: "Clear search", hi: "खोज हटाएँ" },
  "lib.hint": {
    en: "New here? Start with Ather Energy. It has a fresh issue and an offer for sale, so you'll see every kind of fact.",
    hi: "पहली बार आए हैं? Ather Energy से शुरू करें। इसमें फ्रेश इश्यू और ओएफएस दोनों हैं, इसलिए आपको हर तरह के तथ्य दिखेंगे।",
  },
  "lib.hintLink": { en: "Open Ather Energy", hi: "Ather Energy खोलें" },
  "lib.notSet": { en: "Set when the final price is fixed", hi: "अंतिम कीमत तय होने पर पता चलेगा" },

  // 17 keyboard shortcuts dialog (copy not in the spec: written per spec section 1, see AKSHAT_TODO)
  "keys.title": { en: "Keyboard shortcuts", hi: "कीबोर्ड शॉर्टकट" },
  "keys.focusInput": { en: "Focus the question box", hi: "सवाल वाले बॉक्स पर जाएँ" },
  "keys.closePanel": { en: "Close a drawer or popover", hi: "ड्रॉअर या पॉपओवर बंद करें" },
  "keys.pages": { en: "Previous or next page", hi: "पिछला या अगला पन्ना" },
  "keys.zoom": { en: "Zoom in or out", hi: "ज़ूम बढ़ाएँ या घटाएँ" },
  "keys.help": { en: "Show this list", hi: "यह सूची दिखाएँ" },
});

export type StringKey = keyof typeof STRINGS;

export function t(key: StringKey, lang: Lang, vars?: Record<string, string | number>): string {
  const entry: Entry = STRINGS[key];
  let s = entry[lang] || entry.en;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  }
  return s;
}

export const ERROR_CODES = [
  "llm_unavailable",
  "models_warming_up",
  "ipo_not_found",
  "page_out_of_range",
  "rate_limited",
  "validation_error",
  "internal_error",
] as const;

/** Friendly message for an API error code; unknown codes fall back to internal_error. */
export function errorMessage(code: string | undefined, lang: Lang): string {
  if (code === "network") return t("err.network", lang);
  const key = `err.${code}` as StringKey;
  return key in STRINGS ? t(key, lang) : t("err.internal_error", lang);
}
