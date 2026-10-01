"use client";

import { BookOpenText, FileText, Prohibit, Scales, TrendUp, Files } from "@phosphor-icons/react";
import Link from "next/link";
import { useRef, useState, type ReactNode } from "react";
import { MarkIcon, type MarkState } from "@/components/facts/VerdictMark";
import { Rich } from "@/components/ui/Rich";
import type { StringKey } from "@/lib/i18n";
import { useT } from "@/lib/useT";

export function Section({ id, heading, children }: { id?: string; heading: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id ?? heading}-h`} className="border-t border-rule py-14 md:py-20">
      <h2 id={`${id ?? heading}-h`} className="text-[1.75rem] font-semibold leading-tight tracking-tight md:text-[2.25rem]">
        {heading}
      </h2>
      {children}
    </section>
  );
}

export function NewToIpos() {
  const { t } = useT();
  const items = [
    { icon: <FileText size={28} />, h: "land.new.1.h", b: "land.new.1.b" },
    { icon: <BookOpenText size={28} />, h: "land.new.2.h", b: "land.new.2.b" },
    { icon: <Files size={28} />, h: "land.new.3.h", b: "land.new.3.b" },
  ] as const;
  return (
    <Section id="new" heading={t("land.new.h")}>
      <div className="mt-10 grid gap-10 md:grid-cols-3">
        {items.map((i) => (
          <div key={i.h}>
            <span className="text-stamp" aria-hidden>{i.icon}</span>
            <h3 className="mt-3 text-lg font-semibold">{t(i.h)}</h3>
            <p className="mt-2 text-muted"><Rich text={t(i.b)} /></p>
          </div>
        ))}
      </div>
    </Section>
  );
}

export function Chatbot() {
  const { t } = useT();
  return (
    <Section id="chatbot" heading={t("land.bot.h")}>
      <p className="mt-4 max-w-2xl text-lg text-muted">{t("land.bot.b")}</p>
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
        <span className="mt-0.5"><MarkIcon state="contradicted" size={20} /></span>
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
      <ol className="relative mt-10 grid gap-10 md:grid-cols-3">
        <span aria-hidden className="absolute left-4 right-4 top-4 hidden h-px bg-rule md:block" />
        {steps.map((n) => (
          <li key={n} className="relative">
            <span className="relative grid h-8 w-8 place-items-center rounded-full border border-rule bg-bg font-mono text-sm">{n}</span>
            <h3 className="mt-4 text-lg font-semibold">{t(`land.steps.${n}.h` as StringKey)}</h3>
            <p className="mt-2 text-muted">{t(`land.steps.${n}.b` as StringKey)}</p>
            {n === 3 && (
              <ul className="mt-4 space-y-2 text-sm">
                {marks.map((m) => (
                  <li key={m.s} className="flex items-start gap-2">
                    <span className="mt-0.5"><MarkIcon state={m.s} size={16} /></span>
                    <span>
                      <strong className="font-semibold">{t(`verdict.${m.s}`)}</strong> – {t(m.k)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
    </Section>
  );
}

export function AskLang() {
  const { t } = useT();
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const toggle = () => {
    if (!audio.current) {
      audio.current = new Audio("/demo/hi_q02.m4a");
      audio.current.onended = () => setPlaying(false);
    }
    if (playing) {
      audio.current.pause();
      audio.current.currentTime = 0;
      setPlaying(false);
    } else {
      void audio.current.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
    }
  };
  return (
    <Section id="lang" heading={t("land.lang.h")}>
      <p className="mt-4 max-w-2xl text-lg text-muted">{t("land.lang.b")}</p>
      <div className="mt-8 max-w-xl">
        <p lang="hi" className="ml-auto w-fit max-w-full rounded-[10px] bg-stamp/10 px-4 py-3 text-lg">{t("land.lang.q")}</p>
        <button
          type="button"
          onClick={toggle}
          className="mt-3 inline-flex h-11 items-center rounded-[6px] border border-rule px-4 text-sm hover:border-stamp active:scale-[0.97]"
        >
          {playing ? t("land.lang.stop") : t("land.lang.play")}
        </button>
      </div>
    </Section>
  );
}

export function WontDo() {
  const { t } = useT();
  const rows = [
    { icon: <Scales size={22} />, k: "land.no.1" },
    { icon: <TrendUp size={22} />, k: "land.no.2" },
    { icon: <Prohibit size={22} />, k: "land.no.3" },
  ] as const;
  return (
    <Section id="wont" heading={t("land.no.h")}>
      <ul className="mt-8 space-y-4">
        {rows.map((r) => (
          <li key={r.k} className="flex items-center gap-3 text-lg">
            <span className="text-muted" aria-hidden>{r.icon}</span>
            {t(r.k)}
          </li>
        ))}
      </ul>
      <p className="mt-6 max-w-2xl text-muted"><Rich text={t("land.no.p")} /></p>
    </Section>
  );
}

export function FinalCta() {
  const { t } = useT();
  return (
    <section className="border-t border-rule py-16 md:py-24">
      <h2 className="max-w-2xl text-[1.75rem] font-semibold leading-tight tracking-tight md:text-[2.25rem]">{t("land.final.h")}</h2>
      <Link
        href="/ipos"
        className="mt-8 inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-bg transition-transform duration-150 active:scale-[0.97]"
      >
        {t("land.final.cta")}
      </Link>
    </section>
  );
}
