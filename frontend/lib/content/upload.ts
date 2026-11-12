// Upload, processing and My uploads copy: docs/phase2/B05_UI_SPEC.md §1, §3, §4, §6.2 (English verbatim).

// {max_mb} comes from the API config (uploads.max_mb = 50).
type Entry = string;

export const UPLOAD = {
  // §1 nav
  "nav.analyse": "Analyse a document",
  "nav.signIn": "Sign in",
  "nav.myUploads": "My uploads",
  "nav.signOut": "Sign out",
  "nav.account": "Account",

  // §3 upload page
  "up.title": "Analyse an IPO document",
  "up.sub": "Upload a Red Herring Prospectus, a draft (DRHP), or a final prospectus. Vidura reads it and builds a report in a few minutes.",
  "up.drop": "Drag a PDF here, or",
  "up.choose": "choose a file",
  "up.helper": "Up to {max_mb} MB. Text PDFs only (not scans).",
  "up.where": "Where to find one",
  "up.whereBody": "Offer documents are public. You can find them on the SEBI website under Filings → Public Issues, or on the NSE and BSE IPO pages.",
  "up.signInButton": "Sign in with Google to upload",
  "up.signInWhy": "We ask you to sign in only to prevent misuse. We don't use your Google data for anything else.",
  "up.limits": "You can analyse {n} documents a day.",
  "up.paused": "Uploads are paused right now. You can still explore the sample reports.",
  "up.consent": "By uploading, you confirm this is a public offer document. Reports for public documents may be visible to anyone with the link.",
  "up.duplicate": "This document was already analysed. Here's its report.",
  "up.hashing": "Checking the file",
  "up.sending": "Uploading",
  // rejections (§3 table)
  "rej.scanned": "This PDF looks like a scan, so there's no text to read. Try the text version from the SEBI or exchange website.",
  "rej.password": "This PDF is password-protected. Please upload an unlocked copy.",
  "rej.too_large": "This file is larger than {max_mb} MB.",
  "rej.hash_mismatch": "The upload didn't finish correctly. Please try again.",
  "rej.too_many_pages": "This document has more than 1,500 pages, which is more than Vidura can handle.",
  "rej.not_offer_document": "This doesn't look like an IPO offer document. Vidura works with RHPs, DRHPs and prospectuses.",
  "rej.quota": "You've reached today's limit of 3 documents. Try again tomorrow.",
  "rej.global_quota": "Vidura has reached today's limit for everyone. Please try again tomorrow.",

  // §4 processing screen
  "proc.title": "Analysing {company}",
  "proc.yourDoc": "your document",
  "proc.sub": "You can leave this page. The report will be saved to My uploads.",
  "proc.detected": "Checking the document",
  "proc.detected.done": "{pages} pages", // shown after the doc-type badge
  "proc.parsed": "Reading every page",
  "proc.parsed.done": "Read {pages} pages",
  "proc.sections": "Finding the sections",
  "proc.sections.done": "Found {n} sections",
  "proc.facts": "Pulling out the key facts",
  "proc.facts.done": "Key facts ready",
  "proc.redflags": "Running the red-flag checks",
  "proc.redflags.done": "13 checks done",
  "proc.risks": "Finding every risk",
  "proc.risks.done": "Found {n} risks",
  "proc.risk_level": "Working out the risk level",
  "proc.risk_level.done": "Risk level ready",
  "proc.simplify": "Explaining risks in plain English",
  "proc.simplify.done": "{done} of {total} explained",
  "proc.simplify.queued": "Top {n} risks are being explained; they appear in the Risks tab as they finish",
  "proc.simplify.none": "Plain-English explanations appear in the Risks tab on request",
  "proc.index": "Preparing questions and answers",
  "proc.index.done": "Ready for questions",
  "proc.seeReady": "See what's ready",
  "proc.stillWorking": "Still working…",
  "proc.warming": "Warming up the language model. The first one takes a little longer.",
  "proc.failed": "Couldn't finish this step",
  "proc.details": "Details",
  // Plain reasons behind Details: not in B05, builder drafts for Akshat's approval.
  "proc.reason.error": "Something went wrong in this step. The rest of the report is not affected.",
  "proc.reason.skipped": "This step needs an earlier step that didn't finish.",
  "proc.drhp": "This is a draft (DRHP). Many amounts are still blank until the final prospectus, so some checks will say Not available.",
  "proc.tryAnother": "Analyse a document",

  // §6.2 my uploads
  "me.title": "My uploads",
  "me.company": "Company",
  "me.type": "Type",
  "me.uploaded": "Uploaded",
  "me.status": "Status",
  "me.open": "Open",
  "me.processing": "Processing",
  "me.ready": "Ready",
  "me.partial": "Partly ready",
  "me.failed": "Failed",
  "me.empty": "You haven't uploaded anything yet.",
} satisfies Record<string, Entry>;
