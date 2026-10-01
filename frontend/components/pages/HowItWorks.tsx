"use client";

import type { StringKey } from "@/lib/i18n";
import { useT } from "@/lib/useT";

function Flow({ prefix, count, heading }: { prefix: "p" | "q"; count: number; heading: string }) {
  const { t } = useT();
  const steps = Array.from({ length: count }, (_, i) => i + 1);
  return (
    <section aria-label={heading} className="mt-12">
      <h2 className="text-xl font-semibold">{heading}</h2>
      <ol className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-flow-col lg:auto-cols-fr">
        {steps.map((n) => (
          <li key={n} className="relative rounded-[10px] border border-rule bg-surface p-4">
            <span className="grid h-7 w-7 place-items-center rounded-full border border-rule font-mono text-xs">{n}</span>
            <h3 className="mt-3 font-semibold">{t(`how.${prefix}${n}.h` as StringKey)}</h3>
            <p className="mt-1 text-sm text-muted">{t(`how.${prefix}${n}.b` as StringKey)}</p>
            {n < count && (
              <svg aria-hidden viewBox="0 0 24 24" className="absolute -right-[14px] top-1/2 z-10 hidden h-6 w-6 -translate-y-1/2 text-muted lg:block" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 12h10M13 8l4 4-4 4" />
              </svg>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function HowItWorks() {
  const { t } = useT();
  return (
    <div className="py-12 md:py-16">
      <h1 className="text-[2.25rem] font-semibold leading-tight tracking-tight md:text-[3rem]">{t("how.title")}</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">{t("how.intro")}</p>
      <Flow prefix="p" count={6} heading={t("how.row1")} />
      <Flow prefix="q" count={5} heading={t("how.row2")} />
      <section className="mt-16 max-w-2xl border-t border-rule pt-4">
        {([1, 2, 3] as const).map((n) => (
          <div key={n} className="border-b border-rule py-5">
            <h2 className="font-semibold">{t(`how.faq${n}.q` as StringKey)}</h2>
            <p className="mt-2 text-muted">{t(`how.faq${n}.a` as StringKey)}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
