import type { Lang } from "@/lib/format";
import { t } from "@/lib/i18n";
import { DOC_SHORT_KEY, type DocKind } from "@/lib/doc";

/** "RHP p.3" / "Prospectus p.3" (spec 7.3.2 chips). */
export function docLabel(doc: DocKind, page: number, lang: Lang): string {
  return t("facts.chip", lang, { doc: t(DOC_SHORT_KEY[doc], lang), n: page });
}
