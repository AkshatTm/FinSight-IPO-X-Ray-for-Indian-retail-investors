"use client";

import { useT } from "@/lib/useT";

// Placeholder shell until step F4 (spec 7.3).
export function FactsPane({ ipoId }: { ipoId: string }) {
  const { t } = useT();
  return (
    <section aria-label={t("facts.title")} data-ipo={ipoId} className="p-4">
      <h2 className="text-lg font-semibold">{t("facts.title")}</h2>
      <p className="text-sm text-muted">{t("facts.sub")}</p>
    </section>
  );
}
