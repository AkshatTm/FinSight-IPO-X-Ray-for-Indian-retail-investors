// Glossary: docs/12_FRONTEND_SPEC.md section 14 (short definitions, EN + HI). The spec gives no
// long definitions, so the drawer shows the short one. The backend /api/glossary should serve
// this same list (spec 14); until then this file is the source.

interface Entry {
  id: string;
  title: string;
  short: string;
}

export const GLOSSARY: Entry[] = [
  { id: "ipo", title: "IPO", short: "When a company sells shares to the public for the first time." },
  { id: "demat", title: "Demat account", short: "An account that holds your shares electronically. You need one to apply in an IPO." },
  { id: "rhp", title: "RHP (Red Herring Prospectus)", short: "The offer document filed before the IPO opens. The price and some amounts are left blank." },
  { id: "prospectus", title: "Prospectus (final)", short: "The version filed after the price is fixed, with the blanks filled in." },
  { id: "drhp", title: "DRHP", short: "The first draft filed with SEBI for review, before the RHP." },
  { id: "sebi", title: "SEBI", short: "India's securities market regulator. It sets the rules for IPOs." },
  { id: "fresh_issue", title: "Fresh issue", short: "New shares created by the company. The money goes to the company." },
  { id: "ofs", title: "Offer for sale (OFS)", short: "Existing owners selling some of their shares. The money goes to them, not the company." },
  { id: "price_band", title: "Price band", short: "The range of prices within which you can bid." },
  { id: "offer_price", title: "Offer price", short: "The final price per share, set after bidding closes." },
  { id: "face_value", title: "Face value", short: "A fixed accounting value per share, like ₹1 or ₹10. It's not the price you pay." },
  { id: "promoter", title: "Promoter", short: "The person or company that controls the company." },
  { id: "brlm", title: "Book running lead manager", short: "A bank hired to manage the IPO." },
  { id: "registrar", title: "Registrar", short: "The firm that processes applications and allots shares." },
  { id: "objects", title: "Objects of the offer", short: "What the company plans to do with the money from the fresh issue." },
  { id: "units", title: "Lakh, crore, million", short: "1 lakh = 1,00,000. 1 crore = 100 lakh. 1 million = 10 lakh. So ₹100 crore = ₹1,000 million." },
  { id: "blank", title: "[●] (blank)", short: "A blank in the RHP for a value that isn't decided yet, usually the price." },
  { id: "gmp", title: "GMP", short: "“Grey market premium”: unofficial trading talk before listing. It's not in the documents and FinSight doesn't track it." },
];

export const glossaryEntry = (id: string) => GLOSSARY.find((g) => g.id === id);
export const glossaryText = (id: string) => {
  const e = glossaryEntry(id);
  return e ? { title: e.title, short: e.short } : null;
};

/** X-Ray field -> glossary term, for the dotted underline on fact labels. */
export const FIELD_TERM: Record<string, string> = {
  fresh_issue_size: "fresh_issue",
  ofs_shares: "ofs",
  ofs_amount: "ofs",
  offer_price: "offer_price",
  price_band: "price_band",
  face_value: "face_value",
  promoters: "promoter",
  book_running_lead_managers: "brlm",
  registrar: "registrar",
  objects_of_offer: "objects",
};
