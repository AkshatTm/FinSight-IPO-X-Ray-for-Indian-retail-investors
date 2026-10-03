"use client";

import { Rich } from "@/components/ui/Rich";
import type { StringKey } from "@/lib/i18n";
import { useT } from "@/lib/useT";

const REPO = "https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors";

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
      <h1 className="text-[2.25rem] font-semibold leading-tight tracking-tight md:text-[3rem]">{t("about.title")}</h1>
      <div className="mt-8">
        <Block h={t("about.who.h")}>
          <p>{t("about.who.b")}</p>
          <p>
            <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex h-11 items-center text-stamp underline underline-offset-4">
              {t("about.who.link")}
            </a>
          </p>
        </Block>
        <Block h={t("about.data.h")}>
          <p>{t("about.data.b")}</p>
        </Block>
        <Block h={t("about.limits.h")}>
          <ul className="list-disc space-y-2 pl-5">
            {([1, 2, 3, 4, 5, 6, 7, 8] as const).map((n) => (
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
