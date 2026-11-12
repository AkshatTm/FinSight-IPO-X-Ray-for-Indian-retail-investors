"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { MarkIcon, type MarkState } from "@/components/facts/VerdictMark";
import { Rich } from "@/components/ui/Rich";
import type { StringKey } from "@/lib/copy";
import { useIpos, useLab } from "@/lib/api/hooks";
import { detectionPct } from "@/lib/labStats";
import { useT } from "@/lib/useT";

/** Heading in the left column, content on the right. On phones it stacks. */
export function Section({ id, heading, children, wide }: { id?: string; heading: string; children: ReactNode; wide?: boolean }) {
  return (
    <section
      id={id}
      aria-labelledby={`${id ?? heading}-h`}
      className={`grid gap-x-12 gap-y-6 border-t border-rule py-12 md:py-16 ${wide ? "" : "md:grid-cols-[minmax(0,5fr)_minmax(0,8fr)]"}`}
    >
      <h2 id={`${id ?? heading}-h`} className="text-2xl font-semibold leading-tight tracking-tight md:text-3xl">
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

/** B05 §2: four blocks after "How Vidura works". */
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
      <h2 className="max-w-2xl text-2xl font-semibold leading-tight tracking-tight md:text-3xl">{t("land.final.h")}</h2>
      <Link
        href="/ipos"
        className="mt-6 inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-on-accent active:scale-[0.97]"
      >
        {t("land.final.cta")}
      </Link>
    </section>
  );
}

/** Five stages as a pipeline, each with a real number where the data has one. */
export function Pipeline() {
  const { t } = useT();
  const { data: ipos } = useIpos();
  const verifier = useLab("verifier").data;
  const pages = (ipos ?? []).reduce((n, i) => n + (i.rhp_pages ?? 0), 0);
  const caught = detectionPct(verifier);
  const marks: { s: MarkState; k: StringKey }[] = [
    { s: "verified", k: "land.marks.verified" },
    { s: "unverifiable", k: "land.marks.unverifiable" },
    { s: "contradicted", k: "land.marks.contradicted" },
  ];
  const stages: { k: string; b: string; stat: string | null; statLabel?: string }[] = [
    { k: "upload", b: "land.pipe.upload.b", stat: "50 MB" , statLabel: "" },
    { k: "parse", b: "land.pipe.parse.b", stat: pages ? pages.toLocaleString("en-US") : null, statLabel: t("land.pipe.pages") },
    { k: "extract", b: "land.pipe.extract.b", stat: "13", statLabel: t("land.pipe.checks") },
    { k: "verify", b: "land.pipe.verify.b", stat: caught !== null ? `${caught}%` : null, statLabel: t("land.pipe.caught") },
    { k: "risk", b: "land.pipe.risk.b", stat: null },
  ];
  return (
    <section id="steps" aria-labelledby="steps-h" className="border-t border-rule py-12 md:py-16">
      <h2 id="steps-h" className="text-2xl font-bold tracking-tight md:text-3xl">{t("land.pipe.h")}</h2>
      <ol className="mt-8 grid gap-4 md:grid-cols-5 md:gap-0">
        {stages.map((st, i) => (
          <li key={st.k} className="relative md:pr-5">
            <div className="flex items-center gap-3">
              <span className="num grid h-9 w-9 shrink-0 place-items-center rounded-full bg-band text-base font-semibold text-on-band">{i + 1}</span>
              {i < stages.length - 1 && <span aria-hidden className="hidden h-px flex-1 bg-rule md:block" />}
            </div>
            <h3 className="mt-3 text-lg font-semibold">{t(`land.pipe.${st.k}` as StringKey)}</h3>
            <p className="mt-1 text-base text-muted">{t(st.b as StringKey)}</p>
            {st.stat && (
              <p className="mt-3 border-t border-rule pt-3">
                <span className="num text-2xl font-bold">{st.stat}</span>
                {st.statLabel && <span className="mt-0.5 block text-sm text-muted">{st.statLabel}</span>}
              </p>
            )}
          </li>
        ))}
      </ol>
      <ul className="mt-8 flex flex-wrap gap-x-8 gap-y-2 text-base">
        {marks.map((m) => (
          <li key={m.s} className="flex items-center gap-2">
            <MarkIcon state={m.s} size={18} />
            <span>
              <strong className="font-semibold">{t(`verdict.${m.s}`)}</strong>: {t(m.k)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
