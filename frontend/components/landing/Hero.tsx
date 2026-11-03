"use client";

import Link from "next/link";
import { SAMPLE_REPORT_DOC_ID } from "@/lib/showcase";
import { useT } from "@/lib/useT";
import { XrayScan } from "./XrayScan";

/** Full-bleed charcoal band: the promise on the left, a live X-ray of a real RHP page on the right. */
export function Hero() {
  const { t } = useT();
  return (
    <section className="relative overflow-hidden bg-band text-on-band">
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_75%_40%,rgba(226,89,27,0.16),transparent_55%)]" />
      <div className="relative mx-auto grid max-w-[1200px] items-center gap-14 px-5 py-14 md:px-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:py-20">
        <div className="rise-in">
          <h1 className="max-w-[18ch] text-[2.5rem] font-bold leading-[1.05] tracking-[-0.03em] md:text-[3.5rem]">{t("land.h1")}</h1>
          <p className="mt-6 max-w-[48ch] text-lg leading-relaxed text-on-band-muted md:text-xl">{t("land.sub")}</p>
          <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-4">
            <Link
              href="/upload"
              className="inline-flex h-12 items-center rounded-[12px] bg-stamp px-7 text-base font-semibold text-on-accent shadow-[0_8px_24px_rgba(226,89,27,0.35)] hover:bg-[var(--stamp-hover)] active:scale-[0.97]"
            >
              {t("land.cta")}
            </Link>
            <Link href={`/reports/${SAMPLE_REPORT_DOC_ID}`} className="inline-flex h-12 items-center text-base font-medium text-on-band underline decoration-on-band-muted underline-offset-[6px] hover:decoration-stamp">
              {t("land.sample")}
            </Link>
          </div>
          <p className="mt-5 text-sm text-on-band-muted">{t("land.free")}</p>
        </div>
        <XrayScan />
      </div>
    </section>
  );
}
