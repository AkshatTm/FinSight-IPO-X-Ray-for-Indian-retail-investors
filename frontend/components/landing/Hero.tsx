"use client";

import Link from "next/link";
import { VerdictMark } from "@/components/facts/VerdictMark";
import { SAMPLE_REPORT_DOC_ID } from "@/lib/showcase";
import { useT } from "@/lib/useT";

// The fresh-issue line of Ather's RHP page 3 (public/landing/ather-rhp-p3.webp, the pipeline's own
// page image, 595.44 x 841.68 pt). The "₹26,260 MILLION" value sits at x 432.6-485.6, y 161.3-168.5;
// the box below is that region as shares of the page.
function PageProof() {
  const { t } = useT();
  return (
    <figure className="relative mx-auto w-full max-w-[400px]" style={{ aspectRatio: "595.44 / 841.68" }}>
      {/* eslint-disable-next-line @next/next/no-img-element -- static page image from the pipeline */}
      <img
        src="/landing/ather-rhp-p3.webp"
        alt={t("land.lens.alt")}
        width={910}
        height={1286}
        className="absolute inset-0 h-full w-full rounded-[4px] border border-rule bg-white shadow-[var(--shadow-float)]"
        draggable={false}
      />
      <span
        aria-hidden
        className="highlight-in absolute rounded-[3px] border-2 border-stamp bg-stamp/10"
        style={{ left: "70.5%", top: "18.5%", width: "14%", height: "2.2%", animationDelay: "250ms" }}
      />
      <figcaption
        className="mark-in absolute left-[8%] top-[23.5%] inline-flex items-center gap-2 rounded-[8px] border border-rule bg-surface px-3 py-1.5 text-sm shadow-[var(--shadow-float)]"
        style={{ animationDelay: "450ms" }}
      >
        <VerdictMark state="verified" />
        <span>{t("land.lens.tag")}</span>
      </figcaption>
    </figure>
  );
}

export function Hero() {
  const { t } = useT();
  return (
    <section className="grid items-center gap-12 py-12 md:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] md:py-16">
      <div className="rise-in">
        <h1 className="max-w-[16ch] font-serif text-4xl font-semibold leading-[1.08] tracking-tight md:text-[3.25rem]">{t("land.h1")}</h1>
        <p className="mt-6 max-w-[52ch] text-lg text-muted">{t("land.sub")}</p>
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          <Link href="/upload" className="inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-bg active:scale-[0.97]">
            {t("land.cta")}
          </Link>
          <Link href={`/reports/${SAMPLE_REPORT_DOC_ID}`} className="inline-flex h-12 items-center text-stamp underline underline-offset-4">
            {t("land.sample")}
          </Link>
        </div>
        <p className="mt-4 text-sm text-muted">{t("land.free")}</p>
      </div>
      <PageProof />
    </section>
  );
}
