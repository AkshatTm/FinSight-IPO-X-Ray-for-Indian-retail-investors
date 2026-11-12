import { t } from "@/lib/copy";
import { DOC_SHORT_KEY, type DocKind } from "@/lib/doc";

/** "RHP p.3" / "Prospectus p.3" (spec 7.3.2 chips). */
export function docLabel(doc: DocKind, page: number): string {
  return t("facts.chip", { doc: t(DOC_SHORT_KEY[doc]), n: page });
}
