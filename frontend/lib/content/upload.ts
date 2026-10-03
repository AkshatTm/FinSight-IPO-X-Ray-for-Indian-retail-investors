// Upload, processing and My uploads copy: docs/phase2/B05_UI_SPEC.md §1, §3, §4, §6.2 (English verbatim).
// Hindi is a builder draft (B05 gives English only); listed in docs/AKSHAT_TODO.md for review.
// {max_mb} comes from the API config (uploads.max_mb = 50).
type Entry = { en: string; hi: string };

export const UPLOAD = {
  // §1 nav
  "nav.analyse": { en: "Analyse a document", hi: "दस्तावेज़ का विश्लेषण करें" },
  "nav.signIn": { en: "Sign in", hi: "साइन इन करें" },
  "nav.myUploads": { en: "My uploads", hi: "मेरे अपलोड" },
  "nav.signOut": { en: "Sign out", hi: "साइन आउट करें" },
  "nav.account": { en: "Account", hi: "खाता" },

  // §3 upload page
  "up.title": { en: "Analyse an IPO document", hi: "आईपीओ दस्तावेज़ का विश्लेषण करें" },
  "up.sub": {
    en: "Upload a Red Herring Prospectus, a draft (DRHP), or a final prospectus. FinSight reads it and builds a report in a few minutes.",
    hi: "रेड हेरिंग प्रॉस्पेक्टस, ड्राफ़्ट (DRHP) या फ़ाइनल प्रॉस्पेक्टस अपलोड करें। FinSight उसे पढ़कर कुछ ही मिनटों में रिपोर्ट बनाता है।",
  },
  "up.drop": { en: "Drag a PDF here, or", hi: "PDF यहाँ खींचें, या" },
  "up.choose": { en: "choose a file", hi: "फ़ाइल चुनें" },
  "up.helper": {
    en: "Up to {max_mb} MB. Text PDFs only (not scans).",
    hi: "{max_mb} MB तक। केवल टेक्स्ट वाले PDF (स्कैन नहीं)।",
  },
  "up.where": { en: "Where to find one", hi: "यह कहाँ मिलेगा" },
  "up.whereBody": {
    en: "Offer documents are public. You can find them on the SEBI website under Filings → Public Issues, or on the NSE and BSE IPO pages.",
    hi: "ऑफ़र दस्तावेज़ सार्वजनिक होते हैं। ये SEBI की वेबसाइट पर Filings → Public Issues में, या NSE और BSE के आईपीओ पन्नों पर मिलते हैं।",
  },
  "up.signInButton": { en: "Sign in with Google to upload", hi: "अपलोड करने के लिए Google से साइन इन करें" },
  "up.signInWhy": {
    en: "We ask you to sign in only to prevent misuse. We don't use your Google data for anything else.",
    hi: "हम साइन इन केवल दुरुपयोग रोकने के लिए कहते हैं। आपके Google डेटा का हम किसी और काम में इस्तेमाल नहीं करते।",
  },
  "up.limits": { en: "You can analyse 3 documents a day.", hi: "आप दिन में 3 दस्तावेज़ों का विश्लेषण कर सकते हैं।" },
  "up.paused": {
    en: "Uploads are paused right now. You can still explore the sample reports.",
    hi: "अभी अपलोड रुके हुए हैं। आप फिर भी सैंपल रिपोर्ट देख सकते हैं।",
  },
  "up.consent": {
    en: "By uploading, you confirm this is a public offer document. Reports for public documents may be visible to anyone with the link.",
    hi: "अपलोड करके आप पुष्टि करते हैं कि यह एक सार्वजनिक ऑफ़र दस्तावेज़ है। सार्वजनिक दस्तावेज़ों की रिपोर्ट लिंक वाला कोई भी देख सकता है।",
  },
  "up.duplicate": {
    en: "This document was already analysed. Here's its report.",
    hi: "इस दस्तावेज़ का विश्लेषण पहले हो चुका है। यह रही इसकी रिपोर्ट।",
  },
  "up.hashing": { en: "Checking the file", hi: "फ़ाइल जाँची जा रही है" },
  "up.sending": { en: "Uploading", hi: "अपलोड हो रहा है" },
  // rejections (§3 table)
  "rej.scanned": {
    en: "This PDF looks like a scan, so there's no text to read. Try the text version from the SEBI or exchange website.",
    hi: "यह PDF स्कैन लगता है, इसलिए इसमें पढ़ने लायक टेक्स्ट नहीं है। SEBI या एक्सचेंज की वेबसाइट से टेक्स्ट वाला संस्करण आज़माएँ।",
  },
  "rej.password": {
    en: "This PDF is password-protected. Please upload an unlocked copy.",
    hi: "यह PDF पासवर्ड से सुरक्षित है। कृपया बिना लॉक वाली कॉपी अपलोड करें।",
  },
  "rej.too_large": { en: "This file is larger than {max_mb} MB.", hi: "यह फ़ाइल {max_mb} MB से बड़ी है।" },
  "rej.hash_mismatch": {
    en: "The upload didn't finish correctly. Please try again.",
    hi: "अपलोड ठीक से पूरा नहीं हुआ। कृपया फिर से कोशिश करें।",
  },
  "rej.too_many_pages": {
    en: "This document has more than 1,500 pages, which is more than FinSight can handle.",
    hi: "इस दस्तावेज़ में 1,500 से ज़्यादा पन्ने हैं, जो FinSight की क्षमता से ज़्यादा है।",
  },
  "rej.not_offer_document": {
    en: "This doesn't look like an IPO offer document. FinSight works with RHPs, DRHPs and prospectuses.",
    hi: "यह आईपीओ ऑफ़र दस्तावेज़ नहीं लगता। FinSight RHP, DRHP और प्रॉस्पेक्टस के साथ काम करता है।",
  },
  "rej.quota": {
    en: "You've reached today's limit of 3 documents. Try again tomorrow.",
    hi: "आप आज की 3 दस्तावेज़ों की सीमा तक पहुँच गए हैं। कल फिर कोशिश करें।",
  },
  "rej.global_quota": {
    en: "FinSight has reached today's limit for everyone. Please try again tomorrow.",
    hi: "FinSight आज सभी के लिए अपनी सीमा तक पहुँच गया है। कृपया कल फिर कोशिश करें।",
  },

  // §4 processing screen
  "proc.title": { en: "Analysing {company}", hi: "{company} का विश्लेषण हो रहा है" },
  "proc.yourDoc": { en: "your document", hi: "आपका दस्तावेज़" },
  "proc.sub": {
    en: "You can leave this page. The report will be saved to My uploads.",
    hi: "आप यह पन्ना छोड़ सकते हैं। रिपोर्ट मेरे अपलोड में सहेजी जाएगी।",
  },
  "proc.detected": { en: "Checking the document", hi: "दस्तावेज़ की जाँच" },
  "proc.detected.done": { en: "{pages} pages", hi: "{pages} पन्ने" }, // shown after the doc-type badge
  "proc.parsed": { en: "Reading every page", hi: "हर पन्ना पढ़ना" },
  "proc.parsed.done": { en: "Read {pages} pages", hi: "{pages} पन्ने पढ़े" },
  "proc.sections": { en: "Finding the sections", hi: "सेक्शन ढूँढना" },
  "proc.sections.done": { en: "Found {n} sections", hi: "{n} सेक्शन मिले" },
  "proc.facts": { en: "Pulling out the key facts", hi: "मुख्य तथ्य निकालना" },
  "proc.facts.done": { en: "Key facts ready", hi: "मुख्य तथ्य तैयार" },
  "proc.redflags": { en: "Running the red-flag checks", hi: "रेड-फ़्लैग जाँचें चलाना" },
  "proc.redflags.done": { en: "13 checks done", hi: "13 जाँचें पूरी" },
  "proc.risks": { en: "Finding every risk", hi: "हर जोखिम ढूँढना" },
  "proc.risks.done": { en: "Found {n} risks", hi: "{n} जोखिम मिले" },
  "proc.risk_level": { en: "Working out the risk level", hi: "जोखिम स्तर तय करना" },
  "proc.risk_level.done": { en: "Risk level ready", hi: "जोखिम स्तर तैयार" },
  "proc.simplify": { en: "Explaining risks in plain English", hi: "जोखिमों को आसान अंग्रेज़ी में समझाना" },
  "proc.simplify.done": { en: "{done} of {total} explained", hi: "{total} में से {done} समझाए गए" },
  "proc.index": { en: "Preparing questions and answers", hi: "सवाल-जवाब की तैयारी" },
  "proc.index.done": { en: "Ready for questions", hi: "सवालों के लिए तैयार" },
  "proc.seeReady": { en: "See what's ready", hi: "जो तैयार है, देखें" },
  "proc.stillWorking": { en: "Still working…", hi: "अभी काम चल रहा है…" },
  "proc.warming": {
    en: "Warming up the language model. The first one takes a little longer.",
    hi: "भाषा मॉडल शुरू हो रहा है। पहला थोड़ा ज़्यादा समय लेता है।",
  },
  "proc.failed": { en: "Couldn't finish this step", hi: "यह चरण पूरा नहीं हो सका" },
  "proc.details": { en: "Details", hi: "विवरण" },
  // Plain reasons behind Details: not in B05, builder drafts for Akshat's approval.
  "proc.reason.error": {
    en: "Something went wrong in this step. The rest of the report is not affected.",
    hi: "इस चरण में कुछ गड़बड़ हुई। रिपोर्ट के बाकी हिस्सों पर इसका असर नहीं है।",
  },
  "proc.reason.skipped": {
    en: "This step needs an earlier step that didn't finish.",
    hi: "इस चरण के लिए एक पिछला चरण ज़रूरी है, जो पूरा नहीं हुआ।",
  },
  "proc.drhp": {
    en: "This is a draft (DRHP). Many amounts are still blank until the final prospectus, so some checks will say Not available.",
    hi: "यह एक ड्राफ़्ट (DRHP) है। फ़ाइनल प्रॉस्पेक्टस तक कई रकमें खाली रहती हैं, इसलिए कुछ जाँचें उपलब्ध नहीं दिखाएँगी।",
  },
  "proc.tryAnother": { en: "Analyse a document", hi: "दस्तावेज़ का विश्लेषण करें" },

  // §6.2 my uploads
  "me.title": { en: "My uploads", hi: "मेरे अपलोड" },
  "me.company": { en: "Company", hi: "कंपनी" },
  "me.type": { en: "Type", hi: "प्रकार" },
  "me.uploaded": { en: "Uploaded", hi: "अपलोड किया" },
  "me.status": { en: "Status", hi: "स्थिति" },
  "me.open": { en: "Open", hi: "खोलें" },
  "me.processing": { en: "Processing", hi: "प्रोसेस हो रहा है" },
  "me.ready": { en: "Ready", hi: "तैयार" },
  "me.partial": { en: "Partly ready", hi: "आंशिक रूप से तैयार" },
  "me.failed": { en: "Failed", hi: "विफल" },
  "me.empty": { en: "You haven't uploaded anything yet.", hi: "आपने अभी तक कुछ अपलोड नहीं किया है।" },
} satisfies Record<string, Entry>;
