"use client";

import { Rich } from "@/components/ui/Rich";
import type { StringKey } from "@/lib/copy";
import { useT } from "@/lib/useT";

const REPO = "https://github.com/AkshatTm/Vidura-IPO-X-Ray";

function Block({ h, children }: { h: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-rule py-8">
      <h2 className="text-xl font-semibold">{h}</h2>
      <div className="mt-3 max-w-2xl space-y-3 text-muted">{children}</div>
    </section>
  );
}

export function About() {
  const { t } = useT();
  return (
    <div className="py-12 md:py-16">
      <h1 className="text-3xl font-semibold leading-tight tracking-tight md:text-[2.5rem]">{t("about.title")}</h1>
      <div className="mt-8">
        <Block h={t("about.who.h")}>
          <p>{t("about.who.b")}</p>
          <p>
            <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex h-11 items-center text-accent-ink underline underline-offset-4">
              {t("about.who.link")}
            </a>
          </p>
        </Block>
        <Block h={t("about.data.h")}>
          <p>{t("about.data.b")}</p>
        </Block>
        <Block h={t("about.limits.h")}>
          <ul className="list-disc space-y-2 pl-5">
            {([1, 2, 4, 5, 6, 7, 8] as const).map((n) => (
              <li key={n}>{t(`about.limits.${n}` as StringKey)}</li>
            ))}
          </ul>
        </Block>
        <Block h={t("about.advice.h")}>
          <p>
            <Rich text={t("land.no.p")} />
          </p>
        </Block>
        <Block h={t("about.licence.h")}>
          <p>{t("about.licence.b")}</p>
        </Block>
      </div>
    </div>
  );
}
