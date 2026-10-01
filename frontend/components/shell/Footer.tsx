"use client";

import { useT } from "@/lib/useT";

const REPO = "https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors";

export function Footer() {
  const { t } = useT();
  return (
    <footer className="mt-24 border-t border-rule">
      <div className="mx-auto max-w-[1120px] space-y-2 px-4 py-8 text-sm text-muted md:px-6">
        <p className="text-text">
          <strong className="font-semibold">{t("footer.notAdviceBold")}</strong> {t("footer.notAdviceRest")}
        </p>
        <p>
          {t("footer.built")} · {t("footer.data")} ·{" "}
          <a href={REPO} target="_blank" rel="noreferrer" className="text-stamp underline underline-offset-2">
            {t("footer.source")}
          </a>
        </p>
      </div>
    </footer>
  );
}
