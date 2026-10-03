// Model Lab copy: docs/12_FRONTEND_SPEC.md section 8 (verbatim where the spec gives text).
// Headings, column and stat labels the spec only names in English are builder drafts in Hindi
// and are listed in docs/AKSHAT_TODO.md.
type Entry = { en: string; hi: string };

export const LAB = {
  "lab.title": { en: "Model Lab", hi: "मॉडल लैब" },
  "lab.intro": {
    en: "FinSight was tested on IPOs it never saw during training. These are the results, including where it falls short.",
    hi: "FinSight को उन आईपीओ पर जाँचा गया जो उसने ट्रेनिंग में कभी नहीं देखे। ये नतीजे हैं, उन जगहों समेत जहाँ यह कमज़ोर है।",
  },
  "lab.shows": { en: "What this shows", hi: "यह क्या दिखाता है" },
  "lab.missing": { en: "No results for this section on this machine yet.", hi: "इस मशीन पर इस हिस्से के नतीजे अभी नहीं हैं।" },

  // 8.1 ladder
  "lab.ladder.h": { en: "Reading the facts (the extractor ladder)", hi: "तथ्य पढ़ना (निकालने के तरीकों की सीढ़ी)" },
  "lab.ladder.shows": {
    en: "Three ways of pulling facts out of a prospectus, scored against values checked by hand.",
    hi: "प्रॉस्पेक्टस से तथ्य निकालने के तीन तरीके, हाथ से जाँचे गए मानों के मुक़ाबले।",
  },
  "lab.col.method": { en: "Method", hi: "तरीका" },
  "lab.col.whole": { en: "Whole document", hi: "पूरा दस्तावेज़" },
  "lab.col.hidden": { en: "Cover page hidden", hi: "कवर पेज छिपा" },
  "lab.col.tested": { en: "Tested on", hi: "जाँच किस पर हुई" },
  "lab.tested": { en: "{n} values, {k} IPOs", hi: "{k} आईपीओ के {n} मान" },
  "lab.rung.rules": { en: "Rules", hi: "नियम" },
  "lab.rung.rules.d": {
    en: "hand-written patterns for the standard cover-page sentence.",
    hi: "कवर पेज के तय वाक्य के लिए हाथ से लिखे पैटर्न।",
  },
  "lab.rung.qa_pretrained": { en: "Pretrained model", hi: "प्रीट्रेंड मॉडल" },
  "lab.rung.qa_pretrained.d": {
    en: "a question-answering model (DeBERTa) used as it comes.",
    hi: "एक सवाल-जवाब मॉडल (DeBERTa), जैसा मिला वैसा इस्तेमाल किया।",
  },
  "lab.rung.qa_finetuned": { en: "Our fine-tuned model", hi: "हमारा फ़ाइन-ट्यून मॉडल" },
  "lab.rung.qa_finetuned.d": {
    en: "the same model trained on about 4,000 examples FinSight labelled automatically.",
    hi: "वही मॉडल, FinSight के अपने-आप लेबल किए लगभग 4,000 उदाहरणों पर ट्रेन किया हुआ।",
  },
  "lab.rung.bilstm_crf": { en: "Small tagging network", hi: "छोटा टैगिंग नेटवर्क" },
  "lab.rung.bilstm_crf.d": {
    en: "a BiLSTM-CRF that tags the words of a page, trained on the same automatic labels, no pretrained knowledge.",
    hi: "एक BiLSTM-CRF जो पन्ने के शब्दों पर टैग लगाता है, उन्हीं अपने-आप बने लेबल पर ट्रेन किया हुआ, बिना पहले से सीखी जानकारी के।",
  },
  "lab.ladder.take": {
    en: "When the cover page is there, simple rules do best because the cover follows a fixed format. When the cover is hidden, the rules drop to {rules_body}% while our model stays at {ft_body}%. Training on automatic labels made the model {delta} points better than the pretrained version.",
    hi: "जब कवर पेज मौजूद होता है, तो साधारण नियम सबसे अच्छा करते हैं क्योंकि कवर एक तय ढाँचे में होता है। कवर छिपाने पर नियम {rules_body}% पर गिर जाते हैं, जबकि हमारा मॉडल {ft_body}% पर रहता है। अपने-आप बने लेबल पर ट्रेनिंग से मॉडल प्रीट्रेंड वर्ज़न से {delta} अंक बेहतर हुआ।",
  },
  "lab.ladder.note": {
    en: "Small test set: {n} values from {k} IPOs. Treat differences of a few points as noise.",
    hi: "छोटा टेस्ट सेट: {k} आईपीओ से {n} मान। कुछ अंकों के अंतर को संयोग मानें।",
  },
  "lab.chart.alt": {
    en: "Bar chart of the share of facts read correctly by each method, with a 95% range.",
    hi: "हर तरीके से सही पढ़े गए तथ्यों का बार चार्ट, 95% दायरे के साथ।",
  },

  // 8.2 heatmap
  "lab.fields.h": { en: "Fact by fact", hi: "तथ्य दर तथ्य" },
  "lab.fields.shows": { en: "Which method gets each fact right.", hi: "कौन सा तरीका कौन सा तथ्य सही पढ़ता है।" },
  "lab.fields.fact": { en: "Fact", hi: "तथ्य" },
  "lab.fields.note": {
    en: "Whole document, tested IPOs. Each fact has about 7 values, so one miss moves a cell by 14 points.",
    hi: "पूरा दस्तावेज़, टेस्ट वाले आईपीओ। हर तथ्य के लगभग 7 मान हैं, इसलिए एक गलती से खाना 14 अंक हिलता है।",
  },

  "lab.fields.click": { en: "Click a number to see examples.", hi: "उदाहरण देखने के लिए किसी संख्या पर क्लिक करें।" },
  "lab.fields.examples": { en: "Examples: {method}, {fact}", hi: "उदाहरण: {method}, {fact}" },
  "lab.fields.read": { en: "Value read", hi: "पढ़ा गया मान" },
  "lab.fields.checked": { en: "Checked by hand", hi: "हाथ से जाँचा गया" },
  "lab.fields.right": { en: "Right", hi: "सही" },
  "lab.fields.wrong": { en: "Wrong", hi: "गलत" },
  "lab.fields.blank": { en: "(nothing read)", hi: "(कुछ नहीं पढ़ा)" },
  "lab.fields.close": { en: "Close examples", hi: "उदाहरण बंद करें" },

  // 8.3 automatic labels
  "lab.weak.h": { en: "Automatic labels", hi: "अपने-आप बने लेबल" },
  "lab.weak.shows": {
    en: "FinSight's model learned from examples labelled by a program, not by people. We checked a random 50 by hand.",
    hi: "FinSight का मॉडल उन उदाहरणों से सीखा जिन्हें किसी प्रोग्राम ने लेबल किया, इंसानों ने नहीं। हमने 50 बेतरतीब उदाहरण हाथ से जाँचे।",
  },
  "lab.weak.examples": { en: "examples created", hi: "उदाहरण बने" },
  "lab.weak.ipos": { en: "IPOs used", hi: "आईपीओ इस्तेमाल हुए" },
  "lab.weak.precision": { en: "audit precision", hi: "ऑडिट की सटीकता" },
  "lab.weak.range": { en: "95% range {lo}–{hi}%", hi: "95% दायरा {lo}–{hi}%" },
  "lab.weak.note": {
    en: "Audit labels were drafted with AI help and reviewed by the author.",
    hi: "ऑडिट लेबल एआई की मदद से बनाए गए और लेखक ने जाँचे।",
  },

  // 8.4 verifier
  "lab.ver.h": { en: "Catching wrong numbers (the verifier)", hi: "गलत आंकड़े पकड़ना (वेरिफ़ायर)" },
  "lab.ver.shows": {
    en: "We planted wrong numbers in correct answers and checked how many FinSight caught.",
    hi: "हमने सही जवाबों में जानबूझकर गलत आंकड़े डाले और देखा कि FinSight ने कितने पकड़े।",
  },
  "lab.ver.caught": { en: "caught", hi: "पकड़े गए" },
  "lab.ver.false": { en: "false alarms", hi: "झूठे अलार्म" },
  "lab.ver.unit": { en: "unit mix-ups caught on unseen IPOs", hi: "अनदेखे आईपीओ पर पकड़ी गई इकाई की गड़बड़ियाँ" },
  "lab.ver.unitFix": { en: "{hits}/{n} after one rule fix", hi: "एक नियम सुधारने के बाद {hits}/{n}" },
  "lab.ver.col.type": { en: "Kind of error", hi: "गलती का प्रकार" },
  "lab.ver.col.n": { en: "Tests", hi: "टेस्ट" },
  "lab.ver.col.ok": { en: "Handled right", hi: "सही संभाले" },
  "lab.ver.type.digit": { en: "Wrong digit", hi: "गलत अंक" },
  "lab.ver.type.scale": { en: "Wrong unit", hi: "गलत इकाई" },
  "lab.ver.type.swap_metric": { en: "Wrong metric", hi: "गलत चीज़" },
  "lab.ver.type.invented": { en: "Invented number", hi: "गढ़ा हुआ आंकड़ा" },
  "lab.ver.type.rounding_ok": { en: "Harmless rounding", hi: "बेअसर राउंडिंग" },
  "lab.ver.type.correct": { en: "Correct number", hi: "सही आंकड़ा" },
  "lab.ver.note": {
    en: "This is a controlled test with planted errors. Real answers are harder.",
    hi: "यह जानबूझकर डाली गई गलतियों वाला नियंत्रित टेस्ट है। असली जवाब ज़्यादा कठिन होते हैं।",
  },

  // 8.5 retrieval
  "lab.ret.h": { en: "Finding the right pages (retrieval) and answers", hi: "सही पन्ने ढूँढना (रिट्रीवल) और जवाब" },
  "lab.ret.shows": {
    en: "How often the right page is among the five FinSight reads, and how its answers score.",
    hi: "कितनी बार सही पन्ना उन पाँच में होता है जिन्हें FinSight पढ़ता है, और इसके जवाब कितने सही हैं।",
  },
  "lab.ret.col.method": { en: "Way of finding pages", hi: "पन्ने ढूँढने का तरीका" },
  "lab.ret.col.recall": { en: "Right page in the five", hi: "सही पन्ना पाँच में" },
  "lab.ret.col.abstain": { en: "Unanswerable questions declined", hi: "बिना जवाब वाले सवाल छोड़े गए" },
  "lab.ret.bm25": { en: "Keyword", hi: "शब्दों से खोज" },
  "lab.ret.dense": { en: "Meaning", hi: "अर्थ से खोज" },
  "lab.ret.hybrid": { en: "Combined", hi: "दोनों मिलाकर" },
  "lab.ret.hybrid+rerank": { en: "Combined + re-check", hi: "दोनों मिलाकर + दोबारा जाँच" },
  "lab.ret.note": {
    en: "56 answerable and 11 unanswerable questions on the tested IPOs. Answer accuracy on real model answers is not measured yet.",
    hi: "टेस्ट वाले आईपीओ पर 56 जवाब वाले और 11 बिना जवाब वाले सवाल। असली मॉडल जवाबों की सटीकता अभी नहीं मापी गई।",
  },

  // 8.6 frontier
  "lab.front.h": { en: "Compared with general chatbots", hi: "आम चैटबॉट से तुलना" },
  "lab.front.shows": {
    en: "The same questions given to a general chatbot with the full PDF.",
    hi: "वही सवाल, पूरी पीडीएफ़ के साथ, एक आम चैटबॉट से पूछे गए।",
  },

  // 8.7 Hindi
  "lab.hi.h": { en: "Hindi", hi: "हिंदी" },
  "lab.hi.shows": { en: "How well FinSight hears and reads Hindi.", hi: "FinSight हिंदी कितनी अच्छी तरह सुनता और पढ़ता है।" },
  "lab.hi.cer": { en: "speech recognition character error on {n} clips", hi: "{n} क्लिप पर बोली पहचान की अक्षर-त्रुटि" },
  "lab.hi.refs": {
    en: "The reference texts have not been checked by the author yet, so this figure is optimistic.",
    hi: "संदर्भ टेक्स्ट अभी लेखक ने नहीं जाँचे हैं, इसलिए यह आंकड़ा ज़रूरत से अच्छा दिख सकता है।",
  },
  "lab.hi.retrieval": { en: "right page in the five, Hindi questions (combined + re-check)", hi: "सही पन्ना पाँच में, हिंदी सवाल (दोनों मिलाकर + दोबारा जाँच)" },
  "lab.hi.line": {
    en: "All the small open models we tried answer Hindi less fluently than English. The number checks still apply.",
    hi: "हमने जितने छोटे ओपन मॉडल आज़माए, सभी हिंदी में अंग्रेज़ी जितने सहज नहीं हैं। आंकड़ों की जाँच फिर भी लागू होती है।",
  },

  // Phase 2 sections: docs/phase2/B05_UI_SPEC.md §7. Headings, the quoted "What this shows" lines
  // and the rewrite honesty line are verbatim; every other line (and all Hindi) is a builder draft
  // listed in docs/AKSHAT_TODO.md.
  "labb.seg.h": { en: "Splitting risks", hi: "जोखिमों को अलग करना" },
  "labb.seg.shows": { en: "How often FinSight separates the risks correctly.", hi: "FinSight कितनी बार जोखिमों को सही तरह अलग करता है।" },
  "labb.seg.f1": { en: "risk boundaries found correctly (F1)", hi: "सही पहचानी गई जोखिम सीमाएँ (F1)" },
  "labb.seg.pr": { en: "precision {p}%, recall {r}%", hi: "प्रिसिज़न {p}%, रिकॉल {r}%" },
  "labb.seg.docs": { en: "documents checked by hand", hi: "हाथ से जाँचे गए दस्तावेज़" },
  "labb.seg.corpus": { en: "on older IPOs without font information", hi: "फ़ॉन्ट जानकारी के बिना पुराने आईपीओ पर" },

  "labb.chk.h": { en: "Reading the financial checks", hi: "वित्तीय जाँचें पढ़ना" },
  "labb.chk.shows": {
    en: "How often the numbers behind the red flags are read correctly, and how often the status matches one worked out by hand.",
    hi: "चेतावनी संकेतों के पीछे के आंकड़े कितनी बार सही पढ़े जाते हैं, और स्थिति कितनी बार हाथ से निकाली गई स्थिति से मेल खाती है।",
  },
  "labb.chk.nvm": { en: "numbers read correctly ({n} values)", hi: "सही पढ़े गए आंकड़े ({n} मान)" },
  "labb.chk.acc": { en: "statuses that match the hand-worked one ({n} checks)", hi: "हाथ से निकाली स्थिति से मेल खाती स्थितियाँ ({n} जाँचें)" },
  "labb.chk.col.gold": { en: "Worked out by hand", hi: "हाथ से निकाली गई" },
  "labb.chk.col.pred": { en: "FinSight", hi: "FinSight" },

  "labb.clf.h": { en: "Sorting risks into categories", hi: "जोखिमों को श्रेणियों में बाँटना" },
  "labb.clf.shows": {
    en: "Four ways of putting each risk in one of ten categories, from a word-count baseline to the large model that made the training labels, scored on risks labelled by hand.",
    hi: "हर जोखिम को दस श्रेणियों में से एक में रखने के चार तरीके, शब्द-गिनती वाले आधार से लेकर उस बड़े मॉडल तक जिसने ट्रेनिंग लेबल बनाए, हाथ से लेबल किए जोखिमों पर जाँचे गए।",
  },
  "labb.clf.col.model": { en: "Model", hi: "मॉडल" },
  "labb.clf.col.f1": { en: "Macro-F1", hi: "मैक्रो-F1" },
  "labb.clf.col.n": { en: "Risks", hi: "जोखिम" },
  "labb.clf.seeds": { en: "± {std} over {k} runs", hi: "{k} रन में ± {std}" },
  "labb.clf.note": {
    en: "The training labels were made by a larger open model, not by people. Only the test set was labelled by hand.",
    hi: "ट्रेनिंग लेबल लोगों ने नहीं, एक बड़े ओपन मॉडल ने बनाए। केवल टेस्ट सेट हाथ से लेबल किया गया।",
  },

  "labb.rw.h": { en: "Plain-English rewrites", hi: "आसान अंग्रेज़ी में दोबारा लिखना" },
  "labb.rw.shows": {
    en: "Whether the rewrites keep the meaning, how much easier they are to read, and how many the checks reject.",
    hi: "क्या दोबारा लिखे वाक्य मतलब बनाए रखते हैं, वे पढ़ने में कितने आसान हैं, और जाँचें कितनों को रोकती हैं।",
  },
  "labb.rw.col.system": { en: "Rewritten by", hi: "किसने लिखा" },
  "labb.rw.col.yes": { en: "Same meaning", hi: "वही मतलब" },
  "labb.rw.col.partly": { en: "Partly", hi: "कुछ हद तक" },
  "labb.rw.col.no": { en: "No", hi: "नहीं" },
  "labb.rw.grade": { en: "school grades easier to read", hi: "स्कूल कक्षा जितना आसान" },
  "labb.rw.gradeSub": { en: "grade level {a} → {b}", hi: "कक्षा स्तर {a} → {b}" },
  "labb.rw.rejected": { en: "of {n} rewrites rejected by the checks", hi: "{n} में से जाँचों ने रोके" },
  "labb.rw.reason.numbers": { en: "a number changed or added", hi: "कोई आंकड़ा बदला या जोड़ा गया" },
  "labb.rw.reason.phrases": { en: "advice-like wording", hi: "सलाह जैसे शब्द" },
  "labb.rw.reason.length": { en: "too long", hi: "बहुत लंबा" },
  "labb.rw.reason.certainty": { en: "more certain than the original", hi: "मूल से ज़्यादा निश्चित" },
  "labb.rw.honest": {
    en: "The rewrites are checked for numbers and certainty, not for every shade of meaning.",
    hi: "दोबारा लिखे वाक्यों में आंकड़े और निश्चितता जाँची जाती है, मतलब की हर बारीकी नहीं।",
  },

  "labb.nov.h": { en: "Unusualness", hi: "असामान्यता" },
  "labb.nov.shows": {
    en: "When FinSight says a past IPO had a similar risk, how often a person agrees, at each similarity cut-off.",
    hi: "जब FinSight कहता है कि किसी पिछले आईपीओ में मिलता-जुलता जोखिम था, तो हर समानता सीमा पर कितनी बार एक व्यक्ति सहमत होता है।",
  },
  "labb.nov.col.tau": { en: "Similarity cut-off", hi: "समानता सीमा" },
  "labb.nov.col.p": { en: "Really similar", hi: "सच में मिलते-जुलते" },
  "labb.nov.col.n": { en: "Pairs checked", hi: "जाँचे गए जोड़े" },
  "labb.nov.chosen": { en: "used", hi: "इस्तेमाल" },

  "labb.rl.h": { en: "Does the risk level match what happened?", hi: "क्या जोखिम स्तर असल नतीजों से मेल खाता है?" },
  "labb.rl.shows": {
    en: "The risk level worked out for past IPOs, set against what their shares did afterwards. This is a check of the level, not a forecast.",
    hi: "पिछले आईपीओ के लिए निकाला गया जोखिम स्तर, उनके शेयरों के बाद के हाल के साथ। यह स्तर की जाँच है, भविष्यवाणी नहीं।",
  },
  "labb.rl.verdict.none": { en: "There is no clear relationship between the risk level and the {outcome}.", hi: "जोखिम स्तर और {outcome} के बीच कोई साफ़ संबंध नहीं है।" },
  "labb.rl.verdict.weak": { en: "There is a weak relationship between the risk level and the {outcome}.", hi: "जोखिम स्तर और {outcome} के बीच कमज़ोर संबंध है।" },
  "labb.rl.verdict.moderate": { en: "There is a moderate relationship between the risk level and the {outcome}.", hi: "जोखिम स्तर और {outcome} के बीच मध्यम संबंध है।" },
  "labb.rl.rho": { en: "Spearman ρ {rho} (95% range {lo} to {hi}), {n} IPOs.", hi: "स्पीयरमैन ρ {rho} (95% दायरा {lo} से {hi}), {n} आईपीओ।" },
  "labb.rl.outcome.listing_day_return": { en: "listing-day return", hi: "लिस्टिंग के दिन का रिटर्न" },
  "labb.rl.outcome.later_return": { en: "later return", hi: "बाद का रिटर्न" },
  "labb.rl.col.level": { en: "Risk level", hi: "जोखिम स्तर" },
  "labb.rl.col.n": { en: "IPOs", hi: "आईपीओ" },
  "labb.rl.col.median": { en: "Median return", hi: "मध्य रिटर्न" },
  "labb.rl.col.range": { en: "Middle half", hi: "बीच का आधा" },
  "labb.rl.note": {
    en: "Past returns are used only to check the level. FinSight does not predict prices.",
    hi: "पिछले रिटर्न केवल स्तर की जाँच के लिए हैं। FinSight कीमतों का अनुमान नहीं लगाता।",
  },

  "labb.sc.h": { en: "Speed and cost", hi: "गति और लागत" },
  "labb.sc.shows": {
    en: "How long each step takes on the machine running the API, and what one upload costs.",
    hi: "होस्ट की गई सेवा पर हर चरण में कितना समय लगता है, और एक अपलोड की लागत कितनी है।",
  },
  "labb.sc.col.stage": { en: "Step", hi: "चरण" },
  "labb.sc.col.p50": { en: "Typical (s)", hi: "आम तौर पर (सेकंड)" },
  "labb.sc.col.p95": { en: "Slow case (s)", hi: "धीमे मामले में (सेकंड)" },
  "labb.sc.docs": { en: "Measured on {n} uploads.", hi: "{n} अपलोड पर मापा गया।" },
  "labb.sc.perPage": { en: "seconds per page", hi: "सेकंड प्रति पन्ना" },
  "labb.sc.cost": { en: "per upload on average", hi: "प्रति अपलोड औसतन" },
  "labb.sc.costMax": { en: "at most {max}", hi: "अधिकतम {max}" },
  "labb.sc.free": { en: "of the monthly free allowance used", hi: "मासिक मुफ़्त सीमा का उपयोग" },

  // 8.8 footer
  "lab.foot": {
    en: "Every number on this page is generated by scripts in the repository from the files in eval_results/.",
    hi: "इस पेज का हर आंकड़ा रिपॉज़िटरी की स्क्रिप्ट से, eval_results/ की फ़ाइलों से बना है।",
  },
  "lab.foot.link": { en: "Read the scripts on GitHub", hi: "GitHub पर स्क्रिप्ट पढ़ें" },
} satisfies Record<string, Entry>;
