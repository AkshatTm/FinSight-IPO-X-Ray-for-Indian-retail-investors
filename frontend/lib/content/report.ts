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
} satisfies Record<string, Entry>;
