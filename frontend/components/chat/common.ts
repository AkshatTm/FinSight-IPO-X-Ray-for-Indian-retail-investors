import type { Lang } from "@/lib/format";
import { t } from "@/lib/i18n";

/** "RHP p.3" / "Prospectus p.3" (spec 7.3.2 chips). */
export function docLabel(doc: "rhp" | "prospectus", page: number, lang: Lang): string {
  return t("facts.chip", lang, { doc: t(doc === "rhp" ? "doc.rhpShort" : "doc.prospectusShort", lang), n: page });
}
