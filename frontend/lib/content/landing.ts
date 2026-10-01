// Landing page copy, docs/12_FRONTEND_SPEC.md section 5 (verbatim). Hindi marked [HI review] in the
// spec is listed in docs/AKSHAT_TODO.md. `[[id|text]]` marks a glossary term (see components/ui/Rich.tsx).
type Entry = { en: string; hi: string };

export const LANDING = {
  // 5.2 hero
  "land.h1": { en: "Read the fine print. All 500 pages of it.", hi: "बारीक़ शर्तें पढ़िए। पूरे 500 पन्ने।" },
  "land.sub": {
    en: "FinSight reads an IPO's offer document for you, pulls out the numbers that matter, and shows you the exact page each one came from.",
    hi: "FinSight आपके लिए आईपीओ का ऑफ़र दस्तावेज़ पढ़ता है, ज़रूरी आंकड़े निकालता है, और हर आंकड़ा किस पन्ने से आया है, वह भी दिखाता है।",
  },
  "land.cta": { en: "Try it on a real IPO", hi: "किसी असली आईपीओ पर आज़माएँ" },
  "land.how": { en: "How it works", hi: "यह कैसे काम करता है" },
  "land.free": {
    en: "Free. No sign-up. Runs on open-source models.",
    hi: "मुफ़्त। कोई साइन-अप नहीं। ओपन-सोर्स मॉडल पर चलता है।",
  },
  "land.lens.alt": {
    en: "Cover page of a Red Herring Prospectus with the fresh issue amount highlighted and marked as matching the document.",
    hi: "रेड हेरिंग प्रॉस्पेक्टस का कवर पेज, जिसमें फ्रेश इश्यू की रकम पर निशान है और वह दस्तावेज़ से मेल खाती दिखती है।",
  },
  "land.lens.tag": { en: "Fresh issue · ₹26,260 million · page 3", hi: "फ्रेश इश्यू · ₹26,260 मिलियन · पन्ना 3" },

  // 5.3 new to IPOs
  "land.new.h": { en: "New to IPOs? Start here.", hi: "आईपीओ में नए हैं? यहाँ से शुरू करें।" },
  "land.new.1.h": { en: "What is an IPO?", hi: "आईपीओ क्या है?" },
  "land.new.1.b": {
    en: "When a company sells its shares to the public for the first time, that's an [[ipo|IPO]] (initial public offering). Anyone with a [[demat|demat account]] can apply for shares.",
    hi: "जब कोई कंपनी पहली बार अपने शेयर आम लोगों को बेचती है, उसे [[ipo|आईपीओ]] कहते हैं। जिसके पास [[demat|डीमैट खाता]] है, वह शेयरों के लिए आवेदन कर सकता है।",
  },
  "land.new.2.h": { en: "What is the RHP?", hi: "आरएचपी क्या है?" },
  "land.new.2.b": {
    en: "Before the IPO opens, the company publishes a Red Herring Prospectus ([[rhp|RHP]]). It's the official document with the details: how much money is being raised, who is selling shares, and what the money will be used for.",
    hi: "आईपीओ खुलने से पहले कंपनी रेड हेरिंग प्रॉस्पेक्टस ([[rhp|RHP]]) जारी करती है। यह आधिकारिक दस्तावेज़ है जिसमें पूरी जानकारी होती है: कितना पैसा जुटाया जा रहा है, कौन शेयर बेच रहा है, और पैसा किस काम में लगेगा।",
  },
  "land.new.3.h": { en: "Why does nobody read it?", hi: "इसे कोई पढ़ता क्यों नहीं?" },
  "land.new.3.b": {
    en: "It's usually 500 to 1,000 pages of legal language. The important numbers are spread across the cover, the offer section and a few tables.",
    hi: "यह आमतौर पर 500 से 1,000 पन्नों का कानूनी भाषा वाला दस्तावेज़ होता है। ज़रूरी आंकड़े कवर पेज, ऑफ़र वाले हिस्से और कुछ तालिकाओं में बिखरे होते हैं।",
  },

  // 5.4 chatbot
  "land.bot.h": { en: "Why not just ask a chatbot?", hi: "किसी चैटबॉट से ही क्यों न पूछ लें?" },
  "land.bot.b": {
    en: "General chatbots can be helpful, but with Indian offer documents they often run into two problems. They can mix up lakh, crore and million, and they rarely show which page a number came from. When it's your money, \"probably right\" isn't good enough.",
    hi: "आम चैटबॉट मददगार हो सकते हैं, पर भारतीय ऑफ़र दस्तावेज़ों के साथ अक्सर दो दिक्कतें आती हैं। वे लाख, करोड़ और मिलियन में गड़बड़ कर सकते हैं, और शायद ही बताते हैं कि आंकड़ा किस पन्ने से आया। जब बात आपके पैसे की हो, तो \"शायद सही\" काफ़ी नहीं है।",
  },
  "land.bot.row1": { en: "A typical chatbot answer", hi: "एक आम चैटबॉट का जवाब" },
  "land.bot.row1v": { en: "\"The fresh issue is ₹800 lakh.\"", hi: "\"फ्रेश इश्यू ₹800 लाख है।\"" },
  "land.bot.row2": { en: "What the document says (page 3)", hi: "दस्तावेज़ में क्या लिखा है (पन्ना 3)" },
  "land.bot.row2v": { en: "\"₹800 crore\"", hi: "\"₹800 करोड़\"" },
  "land.bot.verdictHead": { en: "Doesn't match.", hi: "मेल नहीं खाता।" },
  "land.bot.verdict": {
    en: "₹800 lakh is ₹8 crore. The document says ₹800 crore. That's 100 times more.",
    hi: "₹800 लाख यानी ₹8 करोड़। दस्तावेज़ में ₹800 करोड़ लिखा है। यह 100 गुना ज़्यादा है।",
  },
  "land.bot.caption": {
    en: "Illustrative example. FinSight's own comparison with general chatbots is in the Model Lab.",
    hi: "यह एक उदाहरण है। आम चैटबॉट से FinSight की तुलना मॉडल लैब में है।",
  },

  // 5.5 how it works
  "land.steps.h": { en: "How FinSight works", hi: "FinSight कैसे काम करता है" },
  "land.steps.1.h": { en: "It reads the whole document.", hi: "यह पूरा दस्तावेज़ पढ़ता है।" },
  "land.steps.1.b": {
    en: "Every page, including the tables, from the RHP and the final prospectus.",
    hi: "हर पन्ना, तालिकाओं समेत, आरएचपी और फ़ाइनल प्रॉस्पेक्टस दोनों से।",
  },
  "land.steps.2.h": { en: "It pulls out the key facts.", hi: "यह मुख्य तथ्य निकालता है।" },
  "land.steps.2.b": {
    en: "Issue size, price, who is selling, what the money is for. Each fact links to its page.",
    hi: "इश्यू का आकार, कीमत, कौन बेच रहा है, पैसा किस काम में लगेगा। हर तथ्य उसके पन्ने से जुड़ा होता है।",
  },
  "land.steps.3.h": { en: "It checks every number in its answers.", hi: "यह अपने हर उत्तर का हर आंकड़ा जाँचता है।" },
  "land.steps.3.b": {
    en: "Ask a question, and each number in the reply gets a mark.",
    hi: "सवाल पूछिए, और जवाब के हर आंकड़े पर एक निशान लगेगा।",
  },
  "land.marks.verified": { en: "the same number is in the document.", hi: "वही आंकड़ा दस्तावेज़ में है।" },
  "land.marks.unverifiable": { en: "the number isn't in the pages used.", hi: "यह आंकड़ा इस्तेमाल किए गए पन्नों में नहीं है।" },
  "land.marks.contradicted": { en: "the document says something different.", hi: "दस्तावेज़ में कुछ और लिखा है।" },

  // 5.6 mini demo
  "land.demo.h": { en: "Try it here", hi: "यहीं आज़माएँ" },
  "land.demo.b": {
    en: "Click a fact. FinSight jumps to the page and highlights where it came from.",
    hi: "किसी तथ्य पर क्लिक करें। FinSight उस पन्ने पर जाकर दिखाएगा कि यह कहाँ से आया।",
  },
  "land.demo.open": { en: "Open the full workspace", hi: "पूरा वर्कस्पेस खोलें" },

  // 5.7 languages
  "land.lang.h": { en: "Ask in English or Hindi", hi: "अंग्रेज़ी या हिंदी में पूछें" },
  "land.lang.b": {
    en: "Type a question, or press the mic and ask in Hindi. You'll see the words FinSight heard before it answers, so you can fix them.",
    hi: "सवाल लिखिए, या माइक दबाकर हिंदी में पूछिए। जवाब देने से पहले आपको दिखेगा कि FinSight ने क्या सुना, ताकि आप उसे ठीक कर सकें।",
  },
  "land.lang.q": { en: "लेंसकार्ट के प्रमोटर कौन हैं?", hi: "लेंसकार्ट के प्रमोटर कौन हैं?" },
  "land.lang.play": { en: "Play the example", hi: "उदाहरण सुनें" },
  "land.lang.stop": { en: "Stop", hi: "रोकें" },

  // 5.8 limits
  "land.no.h": { en: "What FinSight won't do", hi: "FinSight क्या नहीं करेगा" },
  "land.no.1": { en: "It won't tell you whether to apply.", hi: "यह नहीं बताएगा कि आपको आवेदन करना चाहिए या नहीं।" },
  "land.no.2": { en: "It won't predict listing prices or profits.", hi: "यह लिस्टिंग कीमत या मुनाफ़े का अनुमान नहीं लगाएगा।" },
  "land.no.3": { en: "It won't rate or rank IPOs.", hi: "यह आईपीओ को रेटिंग या रैंक नहीं देगा।" },
  "land.no.p": {
    en: "In India, investment advice can only come from advisers registered with [[sebi|SEBI]]. FinSight sticks to what the documents say.",
    hi: "भारत में निवेश सलाह केवल [[sebi|सेबी]] में पंजीकृत सलाहकार ही दे सकते हैं। FinSight केवल वही बताता है जो दस्तावेज़ों में लिखा है।",
  },

  // 5.9 stats
  "land.open.h": { en: "Built in the open", hi: "खुले तरीके से बनाया गया" },
  "land.open.b": {
    en: "Every number below comes from tests you can rerun from the source code.",
    hi: "नीचे दिया हर आंकड़ा उन टेस्ट से आया है जिन्हें आप सोर्स कोड से दोबारा चला सकते हैं।",
  },
  "land.stat.ipos": { en: "IPOs read", hi: "आईपीओ पढ़े गए" },
  "land.stat.pages": { en: "pages processed", hi: "पन्ने पढ़े गए" },
  "land.stat.detect": { en: "of planted number errors caught", hi: "जानबूझकर डाली गई गलतियों में से पकड़ी गईं" },
  "land.stat.robust": {
    en: "accuracy of our model when the cover page is hidden",
    hi: "कवर पेज छिपाने पर हमारे मॉडल की सटीकता",
  },
  "land.open.lab": { en: "See the full results", hi: "पूरे नतीजे देखें" },
  "land.open.code": { en: "Read the code on GitHub", hi: "GitHub पर कोड पढ़ें" },

  // 5.10 final
  "land.final.h": { en: "Pick an IPO and see what's inside.", hi: "कोई आईपीओ चुनें और देखें कि उसमें क्या है।" },
  "land.final.cta": { en: "Browse IPOs", hi: "आईपीओ देखें" },
} satisfies Record<string, Entry>;
