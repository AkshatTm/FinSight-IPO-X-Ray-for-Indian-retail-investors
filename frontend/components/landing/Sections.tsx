"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { MarkIcon, type MarkState } from "@/components/facts/VerdictMark";
import { Rich } from "@/components/ui/Rich";
import type { StringKey } from "@/lib/copy";
import { useT } from "@/lib/useT";

/** Heading in the left column, content on the right. On phones it stacks. */
export function Section({ id, heading, children, wide }: { id?: string; heading: string; children: ReactNode; wide?: boolean }) {
  return (
    <section
      id={id}
      aria-labelledby={`${id ?? heading}-h`}
      className={`grid gap-x-12 gap-y-6 border-t border-rule py-12 md:py-16 ${wide ? "" : "md:grid-cols-[minmax(0,5fr)_minmax(0,8fr)]"}`}
    >
      <h2 id={`${id ?? heading}-h`} className="font-serif text-2xl font-semibold leading-tight tracking-tight md:text-3xl">
        {heading}
      </h2>
      <div className="min-w-0 [&>*:first-child]:mt-0">{children}</div>
    </section>
  );
}

export function NewToIpos() {
  const { t } = useT();
  const items = [
    { h: "land.new.1.h", b: "land.new.1.b" },
    { h: "land.new.2.h", b: "land.new.2.b" },
    { h: "land.new.3.h", b: "land.new.3.b" },
  ] as const;
  return (
    <Section id="new" heading={t("land.new.h")}>
      <dl className="divide-y divide-rule">
        {items.map((i) => (
          <div key={i.h} className="py-5 first:pt-0 last:pb-0">
            <dt className="font-semibold">{t(i.h)}</dt>
            <dd className="mt-1.5 max-w-[62ch] text-muted">
              <Rich text={t(i.b)} />
            </dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

export function Chatbot() {
  const { t } = useT();
  return (
    <Section id="chatbot" heading={t("land.bot.h")}>
      <p className="max-w-[62ch] text-lg text-muted">{t("land.bot.b")}</p>
      <div className="mt-8 max-w-xl overflow-hidden rounded-[10px] border border-rule bg-surface">
        <dl>
          <div className="border-b border-rule p-4">
            <dt className="text-sm text-muted">{t("land.bot.row1")}</dt>
            <dd className="mt-1 text-lg">{t("land.bot.row1v")}</dd>
          </div>
          <div className="p-4">
            <dt className="text-sm text-muted">{t("land.bot.row2")}</dt>
            <dd className="mt-1 text-lg">{t("land.bot.row2v")}</dd>
          </div>
        </dl>
      </div>
      <p className="mt-5 flex max-w-xl items-start gap-2">
        <span className="mt-0.5">
          <MarkIcon state="contradicted" size={20} />
        </span>
        <span>
          <strong className="font-semibold text-[var(--bad)]">{t("land.bot.verdictHead")}</strong> {t("land.bot.verdict")}
        </span>
      </p>
      <p className="mt-4 text-sm text-muted">{t("land.bot.caption")}</p>
    </Section>
  );
}

export function Steps() {
  const { t } = useT();
  const marks: { s: MarkState; k: StringKey }[] = [
    { s: "verified", k: "land.marks.verified" },
    { s: "unverifiable", k: "land.marks.unverifiable" },
    { s: "contradicted", k: "land.marks.contradicted" },
  ];
  const steps = [1, 2, 3] as const;
  return (
    <Section id="steps" heading={t("land.steps.h")}>
      <ol className="divide-y divide-rule">
        {steps.map((n) => (
          <li key={n} className="grid grid-cols-[2rem_1fr] gap-x-3 py-5 first:pt-0 last:pb-0">
            <span className="pt-0.5 font-serif text-xl text-muted">{n}</span>
            <div>
              <h3 className="font-semibold">{t(`land.steps.${n}.h` as StringKey)}</h3>
              <p className="mt-1.5 max-w-[62ch] text-muted">{t(`land.steps.${n}.b` as StringKey)}</p>
              {n === 3 && (
                <ul className="mt-4 space-y-2 text-sm">
                  {marks.map((m) => (
                    <li key={m.s} className="flex items-start gap-2">
                      <span className="mt-0.5">
                        <MarkIcon state={m.s} size={16} />
                      </span>
                      <span>
                        <strong className="font-semibold">{t(`verdict.${m.s}`)}</strong>: {t(m.k)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </li>
        ))}
      </ol>
    </Section>
  );
}

/** B05 §2: four blocks after "How FinSight works". */
export function WhatYouGet() {
  const { t } = useT();
  const blocks = [1, 2, 3, 4] as const;
  return (
    <Section id="get" heading={t("land.get.h")}>
      <dl className="divide-y divide-rule">
        {blocks.map((n) => (
          <div key={n} className="py-5 first:pt-0 last:pb-0">
            <dt className="font-semibold">{t(`land.get.${n}.h` as StringKey)}</dt>
            <dd className="mt-1.5 max-w-[62ch] text-muted">{t(`land.get.${n}.b` as StringKey)}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

export function WontDo() {
  const { t } = useT();
  const rows = ["land.no.1", "land.no.2", "land.no.3"] as const;
  return (
    <Section id="wont" heading={t("land.no.h")}>
      <ul className="max-w-[62ch] space-y-2 text-lg">
        {rows.map((k) => (
          <li key={k}>{t(k)}</li>
        ))}
      </ul>
      <p className="mt-6 max-w-[62ch] text-muted">
        <Rich text={t("land.no.p")} />
      </p>
    </Section>
  );
}

export function FinalCta() {
  const { t } = useT();
  return (
    <section className="border-t border-rule py-14 md:py-20">
      <h2 className="max-w-2xl font-serif text-2xl font-semibold leading-tight tracking-tight md:text-3xl">{t("land.final.h")}</h2>
      <Link
        href="/ipos"
        className="mt-6 inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-bg active:scale-[0.97]"
      >
        {t("land.final.cta")}
      </Link>
    </section>
  );
}
