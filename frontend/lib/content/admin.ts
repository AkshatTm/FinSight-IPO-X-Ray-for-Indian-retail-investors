// /admin/costs copy (B3.5a). Not in B05: every line is a builder draft (EN and HI), listed in
// docs/AKSHAT_TODO.md for review. The page is for the admin only.
type Entry = { en: string; hi: string };

export const ADMIN = {
  "admin.title": { en: "Costs and failed jobs", hi: "लागत और विफल जॉब" },
  "admin.intro": {
    en: "Estimates from each job's run time and the configured Cloud Run size. The billing page is the truth.",
    hi: "हर जॉब के चलने के समय और तय Cloud Run आकार से अनुमान। सही आँकड़े बिलिंग पेज पर हैं।",
  },
  "admin.provisional": {
    en: "Provisional: the rates are Tier 1 list prices; check them for the chosen region.",
    hi: "अस्थायी: दरें Tier 1 की सूची कीमतें हैं; चुने गए क्षेत्र के लिए इन्हें जाँचें।",
  },
  "admin.usdIncomplete": {
    en: "Some jobs used a GPU without a configured rate, so the dollar total is too low.",
    hi: "कुछ जॉब ने बिना तय दर वाले GPU का उपयोग किया, इसलिए डॉलर का कुल कम है।",
  },
  "admin.window": { en: "Last {n} days", hi: "पिछले {n} दिन" },
  "admin.uploads": { en: "Uploads", hi: "अपलोड" },
  "admin.jobs": { en: "Jobs", hi: "जॉब" },
  "admin.failed": { en: "Failed", hi: "विफल" },
  "admin.vcpu": { en: "vCPU-seconds", hi: "vCPU-सेकंड" },
  "admin.gib": { en: "GiB-seconds", hi: "GiB-सेकंड" },
  "admin.gpu": { en: "GPU-seconds", hi: "GPU-सेकंड" },
  "admin.usd": { en: "Estimate (USD)", hi: "अनुमान (USD)" },
  "admin.date": { en: "Day (IST)", hi: "दिन (IST)" },
  "admin.freeShare": {
    en: "Free monthly grant used: {vcpu} of vCPU-seconds, {gib} of GiB-seconds.",
    hi: "मासिक मुफ़्त सीमा का उपयोग: vCPU-सेकंड का {vcpu}, GiB-सेकंड का {gib}।",
  },
  "admin.noJobs": { en: "No jobs in this window.", hi: "इस अवधि में कोई जॉब नहीं।" },
  "admin.failedTitle": { en: "Failed jobs", hi: "विफल जॉब" },
  "admin.noFailed": { en: "No failed jobs.", hi: "कोई विफल जॉब नहीं।" },
  "admin.stage": { en: "Stage", hi: "चरण" },
  "admin.error": { en: "Error", hi: "त्रुटि" },
  "admin.document": { en: "Document", hi: "दस्तावेज़" },
  "admin.signIn": { en: "Sign in with the admin account to see this page.", hi: "यह पेज देखने के लिए एडमिन खाते से साइन इन करें।" },
  "err.forbidden": { en: "This page is only for the FinSight admin.", hi: "यह पेज केवल FinSight एडमिन के लिए है।" },
} satisfies Record<string, Entry>;
