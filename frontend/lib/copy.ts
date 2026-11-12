// Every UI string, English only. Page-level copy lives in ./content/*.ts.
// Interpolation: {name}.

import { LANDING } from "./content/landing";
import { LAB } from "./content/lab";
import { PAGES } from "./content/pages";
import { REPORT } from "./content/report";
import { UPLOAD } from "./content/upload";

const d = <T extends Record<string, string>>(x: T) => x;

export const STRINGS = d({
  ...LANDING,
  ...PAGES,
  ...LAB,
  ...UPLOAD,
  ...REPORT,
  // 3.1 navigation
  "nav.home": "Vidura",
  "nav.ipos": "IPOs",
  "nav.how": "How it works",
  "nav.lab": "Model Lab",
  "nav.about": "About",
  "nav.try": "Try it",
  "nav.menu": "Menu",
  "nav.close": "Close",
  "nav.theme": "Theme",
  "nav.skip": "Skip to content",

  // 3.2 health dot
  "health.label": "Server status",
  "health.ok": "Everything is running",
  "health.warming": "Models are loading. This takes about 20 seconds the first time.",
  "health.degraded": "Running with reduced features. {detail}",
  "health.unreachable": "Can't reach the Vidura server. Demo answers still work.",

  // 3.3 footer
  "footer.notAdviceBold": "Not investment advice.",
  "footer.notAdviceRest": "Vidura explains what public IPO documents say. It does not tell you whether to apply.",
  "footer.built": "Built by Akshat Tomar for CSE472 (Deep Learning for NLP), Lovely Professional University",
  "footer.data": "Data: public SEBI filings",
  "footer.source": "Source code on GitHub",

  // 4 global states
  "banner.coldBold": "Getting ready.",
  "banner.coldRest": "The models are loading on this computer. Answers will start in about 20 seconds.",
  "banner.dismiss": "Dismiss",
  "toast.copied": "Answer copied with page numbers.",
  "toast.linkCopied": "Link copied.",
  "error.title": "Something went wrong here.",
  "error.retry": "Try again",
  "loading": "Loading",
  "glossary.what": "What is {term}?",
  "glossary.more": "More in the glossary",

  // 2.4 / 7.6 verdict marks
  "verdict.verified": "Matches",
  "verdict.unverifiable": "Couldn't check",
  "verdict.contradicted": "Doesn't match",
  "verdict.placeholder": "Blank in RHP",
  "evidence.title.verified": "This number matches",
  "evidence.title.unverifiable": "This number couldn't be checked",
  "evidence.title.contradicted": "This number doesn't match",

  // 3 units (7.3.3)
  "lib.chart.h": "How big each IPO is",
  "lib.chart.sub": "Issue size in ₹ crore, split into new shares from the company and shares sold by existing holders.",
  "lib.fresh.name": "Fresh issue",
  "lib.ofs.name": "Offer for sale",
  "unit.crore": "₹ crore",
  "unit.million": "₹ million",
  "unit.lakh": "₹ lakh",
  "unit.full": "₹ (full)",
  "unit.tooltip": "Change how amounts are shown. The document's own wording is kept in the source view.",

  // 7.5.3 stage line
  "stage.guard": "Checking the question",
  "stage.retrieving": "Finding the right pages",
  "stage.generating": "Writing the answer",
  "stage.verifying": "Checking every number",


  // 13.1 verdict reasons
  "reason.verified": "This number is in the document, for the same item, on {doc} page {page}.",
  "reason.scale_mismatch": "Wrong unit. The answer says {a} ({a_crore}). The document says {b} ({b_crore}). That's {factor} times different.",
  "reason.wrong_value": "Different number. For {metric}, the document says {b} on {doc} page {page}.",
  "reason.wrong_metric": "This number belongs to {other_metric}, not {metric}.",
  "reason.not_found": "This number doesn't appear in the pages used for this answer. It may still be correct, but Vidura couldn't confirm it.",
  "reason.placeholder": "The RHP leaves this blank ([●]). It's filled in later, in the final prospectus.",

  // 13.2 faithfulness meter
  "meter.none": "No numbers to check in this answer.",
  "meter.all": "{n} of {n} numbers match the document",
  "meter.some": "{v} of {n} numbers match. {u} couldn't be checked.",
  "meter.bad": "{c} number(s) don't match the document. Check the marked ones.",

  // 13.3 guard cards
  "guard.advice.title": "I can't tell you whether to invest.",
  "guard.advice.body": "In India, only advisers registered with SEBI can give investment advice. Here's what the documents say, so you can decide for yourself or ask an adviser.",
  "guard.advice.sebi": "What is SEBI?",
  "guard.forecast.title": "I can't predict prices or profits.",
  "guard.forecast.body": "The documents describe the past and the plan, not the future. I can show what they say about past results or how the money will be used.",
  "guard.forecast.chipMoney": "What will the money be used for?",
  "guard.forecast.chipPast": "Past revenue and profit",
  "guard.privacy.title": "I don't share personal details.",
  "guard.privacy.body": "Offer documents list home addresses and contact details of some people. Vidura doesn't show them, even though they're public. I can tell you who the promoters and directors are and their roles.",

  // 13.4 abstain
  "abstain.title": "I couldn't find this in the documents.",
  "abstain.body": "Rather than guess, Vidura only answers from the pages. The closest page it found is below.",
  "abstain.tryDifferent": "Try asking it differently",
  "common.showInDocument": "Show in document",

  // 13.5 API error codes
  "err.llm_unavailable": "The answer model isn't running right now. Try again in a minute. Demo questions still work.",
  "err.models_warming_up": "The models are still loading. This takes about 20 seconds the first time.",
  "err.ipo_not_found": "We couldn't find that IPO.",
  "err.page_out_of_range": "That page isn't in this document.",
  "err.rate_limited": "Too many questions at once. Wait a few seconds.",
  "err.validation_error": "Something about that question didn't work. Try rephrasing it.",
  "err.internal_error": "Something went wrong on our side. Try again.",
  "err.network": "Can't reach the Vidura server. Check that it's running.",

  // 7.9 tour
  "tour.1": "These are the key facts from the offer document. Click one.",
  "tour.2": "This is the real page. The box shows exactly where the fact came from.",
  "tour.3": "Ask a question. Every number in the answer gets a mark.",
  "tour.next": "Next",
  "tour.done": "Got it",
  "tour.skip": "Skip tour",

  // 11 error pages
  "404.title": "This page doesn't exist.",
  "404.body": "The link may be old. Try the IPO list.",
  "404.button": "Browse IPOs",
  "500.title": "Something broke on our side.",
  "500.body": "Reloading usually fixes it. If not, the demo pages still work.",
  "500.button": "Reload",

  // 6 IPO Library
  "lib.title": "IPOs",
  "lib.sub": "{n} recent IPOs from the NSE and BSE. Pick one to see its facts, the original pages, and ask questions.",
  "lib.search": "Search by company or sector",
  "lib.sort.newest": "Newest first",
  "lib.sort.largest": "Largest issue first",
  "lib.sort.az": "A to Z",
  "lib.sort.label": "Sort",
  "lib.filter.all": "All",
  "lib.filter.fresh": "Has fresh issue",
  "lib.filter.ofs": "Only offer for sale",
  "lib.listed": "Listed {month}",
  "lib.issueSize": "Issue size",
  "lib.pages": "{n} pages",
  "lib.fresh": "Fresh {x}",
  "lib.ofsPct": "OFS {y}",
  "lib.onlyOfs": "Only offer for sale",
  "lib.offerPrice": "Offer price",
  "lib.faceValue": "Face value",
  "lib.managers": "Lead managers",
  "lib.empty": "No IPO matches “{query}”. Try a company name like Lenskart.",
  "lib.clear": "Clear search",
  "lib.hint": "New here? Start with Ather Energy. It has a fresh issue and an offer for sale, so you'll see every kind of fact.",
  "lib.hintLink": "Open Ather Energy",
  "lib.report": "Full report",
  "lib.notSet": "Set when the final price is fixed",

  // 7.1 / 7.2 workspace
  "ws.tab.facts": "Facts",
  "ws.tab.document": "Document",
  "ws.tab.ask": "Ask",
  "ws.back": "All IPOs",
  "ws.backReport": "Back to the report",
  "ws.offerPrice": "Offer price",
  "ws.issueSize": "Issue size",
  "ws.listed": "Listed",
  "ws.bidClosed": "Bid closed",
  "ws.bidClosedValue": "{date} (Prospectus p. {page})",
  "ws.glossary": "Glossary",
  "ws.inspect": "Inspect",
  "ws.inspectTip": "See how the last answer was made",
  "ws.resize": "Resize panes",
  "facts.title": "Key facts",
  "facts.sub": "Click any fact to see it on the page.",
  "ask.title": "Ask about {company}",

  // 7.4 document pane
  "doc.rhp": "RHP",
  "doc.prospectus": "Final prospectus",
  "doc.rhpShort": "RHP",
  "doc.prospectusShort": "Prospectus",
  "doc.drhpShort": "DRHP",
  "doc.rhpTip": "Published before the price was set. Some amounts are blank ([●]).",
  "doc.prospectusTip": "Published after the price was set. Blanks are filled in.",
  "doc.pageWord": "Page",
  "doc.ofTotal": "of {total}",
  "doc.prev": "Previous page",
  "doc.next": "Next page",
  "doc.zoomFit": "Fit width",
  "doc.zoom100": "100%",
  "doc.zoom150": "150%",
  "doc.jump": "Jump to section",
  "doc.thumbs": "Thumbnails",
  "doc.pageLabel": "Page number",
  "doc.more": "More: zoom, sections, thumbnails",
  "doc.pageOf": "Page {n} / {total}",
  "doc.pageImageAlt": "{doc} page {n}",
  "doc.section.cover": "Cover page",
  "doc.section.the_offer": "The offer",
  "doc.section.capital_structure": "Share capital",
  "doc.section.objects_of_the_offer": "Use of the money",
  "doc.section.promoters": "Promoters",
  "doc.section.general_information": "General information",

  // 7.3 Facts
  "facts.group.offer": "The offer",
  "facts.group.split": "Money split",
  "facts.group.people": "People",
  "facts.group.use": "Use of the money",
  "facts.perShare": "per share",
  "facts.chip": "{doc} p.{n}",
  "facts.filled": "Filled in the final prospectus",
  "facts.more": "+{n} more",
  "facts.less": "Show fewer",
  "facts.showOnPage": "Press Enter to show on page.",
  "facts.details": "Details",
  "facts.loadingRows": "Loading facts",
  "pop.found": "Found on {doc} page {page}",
  "pop.readBy": "Read by",
  "pop.confidence": "Confidence",
  "pop.asWritten": "As written",
  "split.title": "Where the money goes",
  "split.company": "To the company (fresh issue)",
  "split.sellers": "To selling shareholders (OFS)",
  "split.helper": "Only the fresh issue part goes to the company. The offer-for-sale part goes to the people selling their shares.",
  "split.pureOfs": "This IPO is only an offer for sale. The company receives none of the money.",
  "split.unknown": "The split will be known once the final price is set.",
  "objects.notSet": "[●] amount not set yet",
  "compare.toggle": "Show how each method read this",
  "compare.foot": "Gold = values checked by hand against the PDF.",

  // 7.5 Ask
  "ask.empty": "Ask anything about this IPO's documents. Each number in the answer will be checked against the pages.",
  "ask.placeholder": "Ask a question",
  "ask.send": "Ask",
  "ask.counter": "{n} of 300",
  "ask.chip.money": "How much money is the company raising?",
  "ask.chip.use": "What will the money be used for?",
  "ask.chip.promoters": "Who are the promoters?",
  "ask.chip.price": "What was the final offer price?",
  "ask.chip.ofs": "Who is selling shares in the offer for sale?",
  "ask.copy": "Copy",
  "ask.answerOf": "Answer",
  "ask.you": "Your question",
  "ask.pastRevenue": "What were the past revenue and profit?",
  "mark.open": "Open the check for {value}",
  "cite.jump": "Show source {n} in the document",

  // 7.6 Evidence drawer
  "ev.inAnswer": "In the answer",
  "ev.inDoc": "In the document",
  "ev.asWritten": "As written",
  "ev.inCrore": "In ₹ crore",
  "ev.inMillion": "In ₹ million",
  "ev.reason": "Reason",
  "ev.source": "Source",
  "ev.sourceLine": "{doc}, page {page}",
  "ev.foot": "Vidura compares numbers with code, not with another AI model.",

  // 7.8 glossary, 7.7 inspector
  "gl.title": "Glossary",
  "gl.search": "Find a term",
  "gl.none": "No term matches that search.",
  "insp.title": "How this answer was made",
  "insp.steps": "Steps and time",
  "insp.pages": "Pages it read",
  "insp.checks": "Number checks",
  "insp.prompt": "Exact instructions sent to the model",
  "insp.dropped": "Considered but not used",
  "insp.empty": "Ask a question first. Then open this to see how the answer was made.",
  "insp.loading": "Loading the record of this answer",
  "insp.col.n": "#",
  "insp.col.doc": "Document",
  "insp.col.page": "Page",
  "insp.col.section": "Section",
  "insp.col.bm25": "Keyword rank",
  "insp.col.dense": "Meaning rank",
  "insp.col.fused": "Combined rank",
  "insp.col.score": "Final score",
  "insp.help.bm25": "How well the words match (BM25)",
  "insp.help.dense": "How close the meaning is (embeddings)",
  "insp.help.score": "Re-checked by a second model that reads question and page together",
  "insp.col.number": "Number",
  "insp.col.written": "As written",
  "insp.col.inr": "In ₹",
  "insp.col.found": "Found in document",
  "insp.col.rule": "Rule",
  "insp.col.result": "Result",
  "insp.ms": "{ms} ms",

  // 17 keyboard shortcuts dialog (copy not in the spec: written per spec section 1, see AKSHAT_TODO)
  "keys.title": "Keyboard shortcuts",
  "keys.focusInput": "Focus the question box",
  "keys.closePanel": "Close a drawer or popover",
  "keys.pages": "Previous or next page",
  "keys.zoom": "Zoom in or out",
  "keys.help": "Show this list",
  // 16 demo mode
  "demo.step": "Demo step {n} of 7 · press the next number",
});

export type StringKey = keyof typeof STRINGS;

export function t(key: StringKey, vars?: Record<string, string | number>): string {
  let s: string = STRINGS[key];
  if (vars) {
    for (const [k, v] of Object.entries(vars)) s = s.split("{" + k + "}").join(String(v));
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
export function errorMessage(code: string | undefined): string {
  if (code === "network") return t("err.network");
  const key = ("err." + code) as StringKey;
  return key in STRINGS ? t(key) : t("err.internal_error");
}
