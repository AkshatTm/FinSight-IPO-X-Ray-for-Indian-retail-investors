"use client";

import { useT } from "@/lib/useT";

// Placeholder shell until step F5 (spec 7.5).
export function AskPane({ ipoId, company }: { ipoId: string; company: string }) {
  const { t } = useT();
  return (
    <section aria-label={t("ws.tab.ask")} data-ipo={ipoId} className="p-4">
      <h2 className="text-lg font-semibold">{t("ask.title", { company })}</h2>
    </section>
  );
}
