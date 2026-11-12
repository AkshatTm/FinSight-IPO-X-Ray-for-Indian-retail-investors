"use client";

import Link from "next/link";
import { Fragment } from "react";
import { useReducedMotion } from "@/components/chat/AnswerText";
import { SAMPLE_REPORT_DOC_ID } from "@/lib/showcase";
import { useT } from "@/lib/useT";
import { XrayLens } from "./XrayLens";

/**
 * Full-bleed charcoal hero over a slow film loop of a document under a saffron scan (generated
 * footage, public/landing/hero-loop.mp4). Left: the promise; right: an X-ray lens over a real RHP
 * page that the visitor drives.
 */
export function Hero() {
  const { t } = useT();
  const reduced = useReducedMotion();
  const words = t("land.h1").split(" ");
  const lit = Math.max(0, words.length - 2); // the last two words carry the accent

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
        <div className="absolute inset-0 bg-[linear-gradient(90deg,var(--band)_8%,rgba(23,22,26,0.82)_42%,rgba(23,22,26,0.35)_100%)]" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-band to-transparent" />
        <div className="hero-grain absolute inset-0" />
      </div>

      <div className="mx-auto grid min-h-[min(calc(100svh-3.5rem),820px)] max-w-[1200px] items-center gap-12 px-5 py-12 md:px-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:py-10">
        <div>
          <p className="hero-word inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/5 px-3 py-1 text-sm text-on-band-muted backdrop-blur-sm" style={{ ["--i" as string]: 0 }}>
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-stamp shadow-[0_0_10px_2px_rgba(226,89,27,0.7)]" />
            {t("land.kicker")}
          </p>
          <h1 className="mt-6 max-w-[16ch] text-[2.6rem] font-bold leading-[1.02] tracking-[-0.035em] md:text-[4rem]">
            {words.map((w, i) => (
              <Fragment key={i}>
                <span className={`hero-word inline-block ${i >= lit ? "hero-lit" : ""}`} style={{ ["--i" as string]: i + 1 }}>
                  {w}
                </span>
                {i < words.length - 1 && " "}
              </Fragment>
            ))}
          </h1>
          <p className="hero-word mt-6 max-w-[46ch] text-lg leading-relaxed text-on-band-muted md:text-xl" style={{ ["--i" as string]: words.length + 1 }}>
            {t("land.sub")}
          </p>
          <div className="hero-word mt-9 flex flex-wrap items-center gap-x-6 gap-y-4" style={{ ["--i" as string]: words.length + 2 }}>
            <Link
              href="/upload"
              className="hero-cta inline-flex h-12 items-center rounded-[12px] bg-stamp px-7 text-base font-semibold text-on-accent shadow-[0_10px_30px_rgba(226,89,27,0.4)] transition-[transform,background-color] duration-150 hover:bg-[var(--stamp-hover)] active:scale-[0.97]"
            >
              {t("land.cta")}
            </Link>
            <Link href={`/reports/${SAMPLE_REPORT_DOC_ID}`} className="inline-flex h-12 items-center text-base font-medium text-on-band underline decoration-on-band-muted underline-offset-[6px] hover:decoration-stamp">
              {t("land.sample")}
            </Link>
          </div>
          <p className="hero-word mt-5 text-sm text-on-band-muted" style={{ ["--i" as string]: words.length + 3 }}>
            {t("land.free")}
          </p>
        </div>
        <div className="hero-word" style={{ ["--i" as string]: 4 }}>
          <XrayLens />
        </div>
      </div>
    </section>
  );
}
