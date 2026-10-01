// How it works, About, 404 and 500 copy: docs/12_FRONTEND_SPEC.md sections 9-11 (verbatim).
// About Hindi is not in the spec; it is a builder draft listed in docs/AKSHAT_TODO.md.
type Entry = { en: string; hi: string };

export const PAGES = {
  // 9 how it works
  "how.title": { en: "How FinSight works", hi: "FinSight कैसे काम करता है" },
  "how.intro": {
    en: "Two parts. The first runs once per IPO and prepares everything. The second runs every time you ask a question.",
    hi: "दो हिस्से। पहला हर आईपीओ के लिए एक बार चलता है और सब कुछ तैयार करता है। दूसरा हर बार चलता है जब आप सवाल पूछते हैं।",
  },
  "how.row1": { en: "Preparing an IPO (once)", hi: "आईपीओ तैयार करना (एक बार)" },
  "how.row2": { en: "Answering a question (every time)", hi: "सवाल का जवाब देना (हर बार)" },
  "how.p1.h": { en: "Read the PDF", hi: "पीडीएफ़ पढ़ना" },
  "how.p1.b": { en: "Text and the position of every word on every page.", hi: "हर पन्ने का टेक्स्ट और हर शब्द की जगह।" },
  "how.p2.h": { en: "Find the sections", hi: "सेक्शन ढूँढना" },
  "how.p2.b": { en: "The cover, the offer, share capital, use of money.", hi: "कवर, ऑफ़र, शेयर पूंजी, पैसे का उपयोग।" },
  "how.p3.h": { en: "Read the tables", hi: "तालिकाएँ पढ़ना" },
  "how.p3.b": { en: "Including the \"₹ in million\" note at the top.", hi: "ऊपर लिखे \"₹ मिलियन में\" समेत।" },
  "how.p4.h": { en: "Pull out facts", hi: "तथ्य निकालना" },
  "how.p4.b": {
    en: "Rules for the fixed cover sentence; our trained model as a cross-check.",
    hi: "कवर के तय वाक्य के लिए नियम; जाँच के लिए हमारा ट्रेन किया मॉडल।",
  },
  "how.p5.h": { en: "Understand the numbers", hi: "आंकड़े समझना" },
  "how.p5.b": {
    en: "₹800 crore and ₹8,000 million become the same value.",
    hi: "₹800 करोड़ और ₹8,000 मिलियन एक ही मान बन जाते हैं।",
  },
  "how.p6.h": { en: "Index the pages", hi: "पन्नों का इंडेक्स" },
  "how.p6.b": { en: "So the right page can be found in a second later.", hi: "ताकि बाद में सही पन्ना पल भर में मिल जाए।" },
  "how.q1.h": { en: "Check the question", hi: "सवाल जाँचना" },
  "how.q1.b": {
    en: "Refuse advice, predictions and personal details.",
    hi: "सलाह, अनुमान और निजी जानकारी के सवाल मना करना।",
  },
  "how.q2.h": { en: "Find the pages", hi: "पन्ने ढूँढना" },
  "how.q2.b": {
    en: "Keyword search and meaning search, then a second check.",
    hi: "शब्दों से खोज और अर्थ से खोज, फिर दूसरी जाँच।",
  },
  "how.q3.h": { en: "Write the answer", hi: "जवाब लिखना" },
  "how.q3.b": {
    en: "A small open model running on this laptop, told to use only those pages.",
    hi: "इसी लैपटॉप पर चलने वाला एक छोटा ओपन मॉडल, जिसे केवल उन्हीं पन्नों का इस्तेमाल करने को कहा गया है।",
  },
  "how.q4.h": { en: "Check every number", hi: "हर आंकड़ा जाँचना" },
  "how.q4.b": { en: "Code compares each number with the pages.", hi: "कोड हर आंकड़े की पन्नों से तुलना करता है।" },
  "how.q5.h": { en: "Show the marks", hi: "निशान दिखाना" },
  "how.q5.b": {
    en: "Matches, couldn't check, or doesn't match.",
    hi: "मेल खाता है, जाँच नहीं हो सकी, या मेल नहीं खाता।",
  },
  "how.faq1.q": { en: "Does it send my questions anywhere?", hi: "क्या मेरे सवाल कहीं भेजे जाते हैं?" },
  "how.faq1.a": {
    en: "No. Everything runs on this computer with open-source models.",
    hi: "नहीं। सब कुछ इसी कंप्यूटर पर ओपन-सोर्स मॉडल से चलता है।",
  },
  "how.faq2.q": { en: "Can it still be wrong?", hi: "क्या यह फिर भी गलत हो सकता है?" },
  "how.faq2.a": {
    en: "Yes. The marks tell you which numbers were checked. Always look at the page for anything important.",
    hi: "हाँ। निशान बताते हैं कि कौन से आंकड़े जाँचे गए। किसी भी ज़रूरी बात के लिए पन्ना ज़रूर देखें।",
  },
  "how.faq3.q": { en: "Why doesn't it give advice?", hi: "यह सलाह क्यों नहीं देता?" },
  "how.faq3.a": {
    en: "Investment advice in India needs SEBI registration. FinSight only explains the documents.",
    hi: "भारत में निवेश सलाह के लिए सेबी पंजीकरण ज़रूरी है। FinSight केवल दस्तावेज़ समझाता है।",
  },

  // 10 about
  "about.title": { en: "About FinSight", hi: "FinSight के बारे में" },
  "about.who.h": { en: "Who made it", hi: "इसे किसने बनाया" },
  "about.who.b": {
    en: "Akshat Tomar, B.Tech CSE, Lovely Professional University, as the course project for CSE472 Deep Learning for NLP (2026).",
    hi: "अक्षत तोमर, बी.टेक सीएसई, लवली प्रोफ़ेशनल यूनिवर्सिटी, CSE472 डीप लर्निंग फ़ॉर एनएलपी (2026) के कोर्स प्रोजेक्ट के रूप में।",
  },
  "about.who.link": { en: "Source code on GitHub", hi: "GitHub पर सोर्स कोड" },
  "about.data.h": { en: "What data it uses", hi: "यह कौन सा डेटा इस्तेमाल करता है" },
  "about.data.b": {
    en: "Public offer documents filed with SEBI for 10 IPOs from 2025, and a public research dataset of older IPO documents (Ghosh et al., CC BY-NC-SA 4.0) used only to train the fact-reading model.",
    hi: "2025 के 10 आईपीओ के लिए सेबी में दाख़िल सार्वजनिक ऑफ़र दस्तावेज़, और पुराने आईपीओ दस्तावेज़ों का एक सार्वजनिक शोध डेटासेट (Ghosh et al., CC BY-NC-SA 4.0), जो केवल तथ्य पढ़ने वाले मॉडल को ट्रेन करने में इस्तेमाल हुआ।",
  },
  "about.limits.h": { en: "Known limits", hi: "ज्ञात सीमाएँ" },
  "about.limits.1": { en: "Covers 10 IPOs, not every IPO.", hi: "यह 10 आईपीओ कवर करता है, हर आईपीओ नहीं।" },
  "about.limits.2": { en: "Scanned PDFs can't be read.", hi: "स्कैन किए गए पीडीएफ़ नहीं पढ़े जा सकते।" },
  "about.limits.3": {
    en: "Hindi answers are less fluent than English ones.",
    hi: "हिंदी जवाब अंग्रेज़ी जवाबों जितने सहज नहीं होते।",
  },
  "about.limits.4": {
    en: "The test sets are small, so scores can move a few points.",
    hi: "टेस्ट सेट छोटे हैं, इसलिए स्कोर कुछ अंक ऊपर-नीचे हो सकते हैं।",
  },
  "about.limits.5": {
    en: "Some evaluation data was drafted with AI help and checked by the author.",
    hi: "कुछ मूल्यांकन डेटा AI की मदद से बनाया गया और लेखक ने उसे जाँचा।",
  },
  "about.advice.h": { en: "Not investment advice", hi: "यह निवेश सलाह नहीं है" },
  "about.licence.h": { en: "Licences", hi: "लाइसेंस" },
  "about.licence.b": {
    en: "Code: MIT. Training data and the trained model: CC BY-NC-SA 4.0 (non-commercial).",
    hi: "कोड: MIT। ट्रेनिंग डेटा और ट्रेन किया गया मॉडल: CC BY-NC-SA 4.0 (गैर-व्यावसायिक)।",
  },

  // 11 404 and 500
  "nf.title": { en: "This page doesn't exist.", hi: "यह पन्ना मौजूद नहीं है।" },
  "nf.body": { en: "The link may be old. Try the IPO list.", hi: "लिंक पुराना हो सकता है। आईपीओ सूची देखें।" },
  "nf.cta": { en: "Browse IPOs", hi: "आईपीओ देखें" },
  "err500.title": { en: "Something broke on our side.", hi: "हमारी तरफ़ से कुछ गड़बड़ हो गई।" },
  "err500.body": {
    en: "Reloading usually fixes it. If not, the demo pages still work.",
    hi: "पेज रीलोड करने से अक्सर ठीक हो जाता है। नहीं तो डेमो पेज फिर भी काम करेंगे।",
  },
  "err500.cta": { en: "Reload", hi: "रीलोड करें" },
} satisfies Record<string, Entry>;
