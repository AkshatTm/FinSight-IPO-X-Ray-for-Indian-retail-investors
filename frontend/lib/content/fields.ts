// Field display rules: docs/12_FRONTEND_SPEC.md section 12 (labels, tooltips, placeholder and
// "not in document" texts).
// docs/AKSHAT_TODO.md under "new copy to review".

type Pair = string;

export interface FieldContent {
  label: Pair;
  tip: Pair;
  /** Shown when the RHP leaves the value blank and the prospectus has none. */
  placeholder?: Pair;
  /** Shown when the field does not exist in the document (e.g. no fresh issue). */
  notInDocument?: Pair;
}

export const FIELD_CONTENT: Record<string, FieldContent> = {
  total_issue_size: {
    label: "Total issue size",
    tip: "The total value of all shares offered in the IPO.",
    placeholder: "Set when the final price is fixed",
  },
  fresh_issue_size: {
    label: "Fresh issue",
    tip: "New shares created by the company. This money goes to the company.",
    placeholder: "Amount blank in the RHP",
    notInDocument: "None. This IPO has no fresh issue.",
  },
  ofs_shares: {
    label: "Offer for sale (shares)",
    tip: "Existing shares being sold by current owners.",
    placeholder: "Number of shares blank in the RHP",
  },
  ofs_amount: {
    label: "Offer for sale (amount)",
    tip: "Money from the offer for sale. It goes to the sellers, not the company.",
    placeholder: "Set when the final price is fixed",
  },
  offer_price: {
    label: "Final offer price",
    tip: "The price per share set at the end of bidding.",
    placeholder: "Not set in the RHP",
  },
  price_band: {
    label: "Price band",
    tip: "The price range for bids. It's announced separately, so the RHP leaves it blank.",
    placeholder: "Announced separately, blank in the RHP",
  },
  face_value: {
    label: "Face value",
    tip: "A fixed accounting value per share. It is not the price you pay.",
  },
  promoters: {
    label: "Promoters",
    tip: "The people or companies that control the company.",
  },
  book_running_lead_managers: {
    label: "Lead managers",
    tip: "Banks that run the IPO process for the company.",
  },
  registrar: {
    label: "Registrar",
    tip: "The firm that handles applications and share allotment.",
  },
  objects_of_offer: {
    label: "Use of the money",
    tip: "What the company says it will do with the fresh issue money.",
    placeholder: "Amount not set yet",
    notInDocument: "Not applicable. The company gets no money from this IPO.",
  },
};

/** Fields whose money value is a price per share, not a total. */
export const PER_SHARE = new Set(["offer_price", "face_value", "price_band"]);

export const GROUPS: { id: "offer" | "people" | "use"; fields: string[] }[] = [
  { id: "offer", fields: ["total_issue_size", "fresh_issue_size", "ofs_shares", "ofs_amount", "offer_price", "price_band", "face_value"] },
  { id: "people", fields: ["promoters", "book_running_lead_managers", "registrar"] },
  { id: "use", fields: ["objects_of_offer"] },
];

export const EXTRACTOR_NAME: Record<string, Pair> = {
  rules: "Rules",
  qa_pretrained: "Pretrained model",
  qa_finetuned: "Our fine-tuned model",
};

export const CHECK_LABEL: Record<string, Pair> = {
  total_equals_fresh_plus_ofs: "Total = fresh issue + offer for sale",
};

export const pick = (p: Pair) => p;
