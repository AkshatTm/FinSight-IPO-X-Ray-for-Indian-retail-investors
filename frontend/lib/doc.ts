/** Offer-document kinds the API returns (B02 §5): RHP, draft RHP and the final Prospectus. */
export type DocKind = "rhp" | "drhp" | "prospectus";

/** i18n key for the short name shown on chips and in sentences ("RHP", "DRHP", "Prospectus"). */
export const DOC_SHORT_KEY = {
  rhp: "doc.rhpShort",
  drhp: "doc.drhpShort",
  prospectus: "doc.prospectusShort",
} as const satisfies Record<DocKind, string>;
