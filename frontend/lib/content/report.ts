// Risk report copy: docs/phase2/B05_UI_SPEC.md §5 (English verbatim). The risk report is English
// only (B05 "Language"), so `hi` repeats the English, except the Hindi note shown at the top of
// these tabs. Lines marked "builder draft" are not in B05 and are listed in docs/AKSHAT_TODO.md.
type Entry = { en: string; hi: string };
const en = (text: string): Entry => ({ en: text, hi: text });

export const REPORT = {
  // Shown only when the UI is in Hindi; the English line is a builder draft.
  "rep.englishOnly": { en: "This risk report is in English only for now.", hi: "यह जोखिम रिपोर्ट अभी केवल अंग्रेज़ी में है।" },

  // §5.6 Compare tab
  "cmp.title": en("How it compares"),
  "cmp.sub": en("With the listed companies the document names as peers, and with {n} past Indian IPOs."),
  "cmp.colCompany": en("Company"),
  "cmp.colPe": en("P/E"),
  "cmp.colEps": en("EPS (₹)"),
  "cmp.colRonw": en("Return on net worth"),
  "cmp.colNav": en("Book value per share"),
  "cmp.source": en("Basis for Offer Price, page {p}"),
  "cmp.tipPe": en("Price divided by yearly profit per share. Higher means investors pay more for each rupee of profit."),
  "cmp.tipRonw": en("Profit as a share of the owners' money in the business."),
  "cmp.pastTitle": en("Against past IPOs"),
  "cmp.metric.issue_size_inr": en("Issue size"),
  "cmp.metric.ofs_share": en("OFS share"),
  "cmp.metric.insider_price_gap": en("Insider price gap"),
  "cmp.metric.pe": en("P/E"),
  "cmp.higherThan": en("Higher than {p}% of past IPOs"),
  "cmp.noPeers": en("The document doesn't name listed peers."),
  "cmp.noData": en("Not enough data to compare."),
  "cmp.issuer": en("This IPO"), // builder draft
  "cmp.provisional": en("Provisional: the past-IPO figures are placeholders until they are computed from 2018–2023 IPOs."), // builder draft
  // §5.1 header and §5.2 tabs
  "rep.analysed": en("Analysed {date}"),
  "rep.share": en("Share"),
  "rep.copied": en("Link copied"), // builder draft
  "rep.ask": en("Ask"),
  "rep.companion": en("Final prospectus also analysed → View"),
  "rep.pages": en("{n} pages"), // builder draft
  "tab.overview": en("Overview"),
  "tab.redflags": en("Red flags"),
  "tab.risks": en("Risks"),
  "tab.compare": en("Compare"),
  "tab.facts": en("Facts"),
  "tab.document": en("Document"),
  "rep.notReady": en("This part isn't ready yet."), // builder draft

  // §5.3 Overview: risk level card
  "rl.title": en("Risk level: {level}"),
  "rl.low": en("Low"),
  "rl.medium": en("Medium"),
  "rl.high": en("High"),
  "rl.line": en("More disclosed risk than {p}% of {n} past Indian IPOs."),
  "rl.show": en("Show the risk level"),
  "rl.why": en("Why"),
  "rl.reason": en("{label} · +{points}"),
  "rl.disclaimer": en(
    "This level summarises the risks this document discloses, compared with past Indian IPOs. It is not a recommendation to apply, buy or avoid, and it does not predict how the shares will perform.",
  ),
  "rl.how": en("How the risk level works"),
  "rl.provisional": en("Provisional: the thresholds are placeholders until they are computed from 2018–2023 IPOs."), // builder draft
  // §6.3 modal
  "rlm.intro": en("FinSight adds up points from the red flags and the most serious unusual risks:"),
  "rlm.points1": en("Each Concern adds 2 points and each Watch adds 1."),
  "rlm.points2": en("Each risk that is highly serious and appears in fewer than 10% of past IPOs adds 1 point (up to 4)."),
  "rlm.share": en("Checks that can't be worked out for this document are left out, so the total is compared as a share of the points that were possible."),
  "rlm.compare": en("Then it compares that share with {n} past Indian IPOs (2018–2023). The lowest third is Low, the middle third is Medium, and the top third is High."),
  "rlm.notAdvice": en("This tells you how much risk the document discloses compared with other IPOs. It does not tell you whether the shares will do well, and it is not advice."),
  "rlm.outcomes": en("See how well this matches past outcomes"),

  // §5.3 Overview: the rest
  "ov.five": en("Five things to know"),
  "ov.readMore": en("Read more"),
  "ov.flags": en("Red flags at a glance"),
  "ov.offerTitle": en("The offer in one line"),
  "ov.offer": en("{company} is raising ₹{fresh} crore for itself, and existing shareholders are selling ₹{ofs} crore. Price ₹{price} per share."),
  "ov.offerOfs": en("The company receives none of the money: all ₹{ofs} crore goes to existing shareholders."),
  "ov.offerDrhp": en("Amounts will be set in the final prospectus."),
  "ov.footer": en("Every number links to its page. Numbers are checked by code, not by an AI model."),

  // §5.4 Red flags tab
  "rf.title": en("Red flags"),
  "rf.sub": en("13 checks that beginners usually miss. Each one is calculated from the numbers in this document."),
  "rf.all": en("All"),
  "rf.concern": en("Concern"),
  "rf.watch": en("Watch"),
  "rf.ok": en("OK"),
  "rf.not_available": en("Not available"),
  "rf.not_applicable": en("Not applicable"), // builder draft (status word; B05 sentences start "Not applicable:")
  // §5.4 red-flag titles
  "rf.t.RF01": en("Profit or loss"),
  "rf.t.RF02": en("Cash from the business"),
  "rf.t.RF03": en("Debt"),
  "rf.t.RF04": en("Who gets the IPO money"),
  "rf.t.RF05": en("What insiders paid"),
  "rf.t.RF06": en("Founders' stake after the IPO"),
  "rf.t.RF07": en("Vague use of money"),
  "rf.t.RF08": en("Court cases"),
  "rf.t.RF09": en("Dealings with related companies"),
  "rf.t.RF10": en("Dependence on a few customers"),
  "rf.t.RF11": en("Price compared with listed peers"),
  "rf.t.RF12": en("Auditor's remarks"),
  "rf.t.RF13": en("Pledged promoter shares"),
  "rf.numbers": en("Numbers used"),
  "rf.how": en("How this check works"),
  "rf.show": en("Show in document"),
  "rf.missing": en("FinSight couldn't find this in the document."),
  "rf.page": en("page {p}"), // builder draft

  // §5.5 Risks tab
  "rk.title": en("Every risk, in plain English"),
  "rk.sub": en("The company lists {n} risks. Here they are in simple words, with the most important first."),
  "rk.sortImportance": en("Most important first"),
  "rk.sortOrder": en("Order in document"),
  "rk.sortCategory": en("By category"),
  "rk.search": en("Search risks"),
  "rk.unusualOnly": en("Show only unusual risks"),
  "rk.sev.high": en("High seriousness"),
  "rk.sev.medium": en("Medium seriousness"),
  "rk.sev.low": en("Low seriousness"),
  "rk.unusual": en("Unusual: in {x}% of past IPOs"),
  "rk.common": en("Common: in {x}% of past IPOs"),
  "rk.inPast": en("In {x}% of past IPOs"),
  "rk.explaining": en("Explaining…"),
  "rk.explain": en("Explain in plain English"),
  "rk.rejected": en("A simple version isn't available for this one, so here is the original."),
  "rk.theirWording": en("Their wording"),
  "rk.hedging": en("Written cautiously, but this describes something that has already happened."),
  "rk.figures": en("Contains figures: {list}"),
  "rk.similar": en("Similar risks in past IPOs"),
  "rk.similarRow": en("{company} ({year}): {title}"),
  "rk.show": en("Show in document"),
  "rk.askAbout": en("Ask about this"),
  "rk.footnote": en("Plain-English versions are written by FinSight's own model and checked: every number must match the original. Always read the original for anything important."),
  "rk.none": en("No risks match."), // builder draft
  "cat.financial": en("Money and profits"),
  "cat.debt_liquidity": en("Debt and cash"),
  "cat.customers_suppliers": en("Customers and suppliers"),
  "cat.competition": en("Competition"),
  "cat.legal_litigation": en("Court cases and legal"),
  "cat.regulatory": en("Rules and regulators"),
  "cat.promoters_governance": en("Promoters and management"),
  "cat.operations": en("Operations"),
  "cat.technology_data": en("Technology and data"),
  "cat.market_macro": en("Economy and market"),
} satisfies Record<string, Entry>;
