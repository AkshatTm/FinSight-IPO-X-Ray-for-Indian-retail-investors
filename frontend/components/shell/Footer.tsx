"use client";

import { useT } from "@/lib/useT";

const REPO = "https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors";

export function Footer() {
  const { t } = useT();
  return (
    <footer className="mt-24 bg-band text-on-band">
      <div className="mx-auto max-w-[1120px] space-y-2 px-4 py-10 text-sm text-on-band-muted md:px-6">
        <p className="text-base text-on-band">
          <strong className="font-semibold">{t("footer.notAdviceBold")}</strong> {t("footer.notAdviceRest")}
        </p>
        <p>
          {t("footer.built")} · {t("footer.data")} ·{" "}
          <a href={REPO} target="_blank" rel="noreferrer" className="text-on-band underline underline-offset-2 hover:text-stamp">
            {t("footer.source")}
          </a>
        </p>
      </div>
    </footer>
  );
}
