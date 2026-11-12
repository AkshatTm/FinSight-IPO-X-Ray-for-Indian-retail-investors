"use client";

import Link from "next/link";
import { useReducedMotion } from "@/components/chat/AnswerText";
import { SAMPLE_REPORT_DOC_ID } from "@/lib/showcase";
import { useT } from "@/lib/useT";
import { ProspectusReel } from "./ProspectusReel";

/**
 * Full-bleed charcoal hero over a slow film loop of a document under a saffron scan (generated
 * footage, public/landing/hero-loop.mp4). Left: the promise; right: a reel of FinSight reading a
 * made-up prospectus page and pulling one fact out of it.
 */
export function Hero() {
  const { t } = useT();
  const reduced = useReducedMotion();
  const h1 = t("land.h1");
  const cut = h1.lastIndexOf(" ", h1.lastIndexOf(" ") - 1); // the last two words carry the accent

  return (
    <section className="relative isolate overflow-hidden bg-band text-on-band">
      <div aria-hidden className="absolute inset-0 -z-10">
        {reduced ? (
          // eslint-disable-next-line @next/next/no-img-element -- decorative still
          <img src="/landing/hero-poster.webp" alt="" className="h-full w-full object-cover object-right opacity-60" />
        ) : (
          <video
            className="h-full w-full object-cover object-right opacity-60"
            src="/landing/hero-loop.mp4"
            poster="/landing/hero-poster.webp"
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
          />
        )}
        <div className="absolute inset-0 bg-[linear-gradient(90deg,var(--band)_10%,rgba(23,22,26,0.85)_45%,rgba(23,22,26,0.45)_100%)]" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-band to-transparent" />
        <div className="hero-grain absolute inset-0" />
      </div>

      <div className="mx-auto grid min-h-[min(calc(100svh-3.5rem),800px)] max-w-[1200px] items-center gap-12 px-4 py-14 md:px-8 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-16 lg:py-12">
        <div>
          <p className="hero-in text-sm text-on-band-muted" style={{ ["--i" as string]: 0 }}>
            {t("land.kicker")}
          </p>
          <h1 className="hero-in mt-4 max-w-[15ch] text-[2.5rem] font-semibold leading-[1.04] tracking-[-0.03em] md:text-[3.5rem]" style={{ ["--i" as string]: 1 }}>
            {h1.slice(0, cut)} <span className="text-stamp">{h1.slice(cut + 1)}</span>
          </h1>
          <p className="hero-in mt-6 max-w-[44ch] text-lg leading-relaxed text-on-band-muted" style={{ ["--i" as string]: 2 }}>
            {t("land.sub")}
          </p>
          <div className="hero-in mt-9 flex flex-wrap items-center gap-x-6 gap-y-4" style={{ ["--i" as string]: 3 }}>
            <Link
              href="/upload"
              className="inline-flex h-12 items-center rounded-[8px] bg-stamp px-6 text-base font-semibold text-on-accent transition-[transform,background-color] duration-150 hover:bg-[var(--stamp-hover)] active:scale-[0.97]"
            >
              {t("land.cta")}
            </Link>
            <Link
              href={`/reports/${SAMPLE_REPORT_DOC_ID}`}
              className="inline-flex h-12 items-center text-base font-medium text-on-band underline decoration-white/30 underline-offset-[6px] transition-[text-decoration-color] duration-150 hover:decoration-stamp"
            >
              {t("land.sample")}
            </Link>
          </div>
          <p className="hero-in mt-6 text-sm text-on-band-muted" style={{ ["--i" as string]: 4 }}>
            {t("land.free")}
          </p>
        </div>
        <div className="hero-in" style={{ ["--i" as string]: 2 }}>
          <ProspectusReel />
        </div>
      </div>
    </section>
  );
}
