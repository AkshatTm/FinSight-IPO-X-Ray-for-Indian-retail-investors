"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiGet, type Schemas } from "@/lib/api/client";
import { useIpos, useLab, useLabB } from "@/lib/api/hooks";
import { risksExplained } from "@/lib/labB";
import { detectionPct, robustPct } from "@/lib/labStats";
import { SAMPLE_REPORT_DOC_ID } from "@/lib/showcase";
import { useT } from "@/lib/useT";
import { Section } from "./Sections";

const REPO = "https://github.com/AkshatTm/Vidura-IPO-X-Ray";

/** Stat blocks; each one is left out when its source value is missing (spec 5.9, B05 §2).
 * "Past IPOs used for comparison" is `corpus_n` from configs/risklevel.yaml as the risk-level
 * endpoint reports it (0 while the thresholds are placeholders, so hidden). */
export function OpenStats() {
  const { t } = useT();
  const { data: ipos } = useIpos();
  const verifier = useLab("verifier").data;
  const ladder = useLab("ladder").data;
  const simplify = useLabB("simplify").data;
  const level = useQuery({
    queryKey: ["risk-level", SAMPLE_REPORT_DOC_ID],
    queryFn: () => apiGet<Schemas["RiskLevel"]>(`/api/docs/${SAMPLE_REPORT_DOC_ID}/risk-level`),
    retry: false,
  }).data;

  const stats: { value: string; label: string }[] = [];
  if (ipos?.length) {
    stats.push({ value: String(ipos.length), label: t("land.stat.ipos") });
    const pages = ipos.reduce((n, i) => n + (i.rhp_pages ?? 0), 0);
    if (pages) stats.push({ value: pages.toLocaleString("en-US"), label: t("land.stat.pages") });
  }
  const det = detectionPct(verifier);
  if (det !== null) stats.push({ value: `${det}%`, label: t("land.stat.detect") });
  const rob = robustPct(ladder);
  if (rob !== null) stats.push({ value: `${rob}%`, label: t("land.stat.robust") });
  const explained = risksExplained(simplify);
  if (explained !== null) stats.push({ value: explained.toLocaleString("en-US"), label: t("land.stat.risks") });
  if (level?.corpus_n) stats.push({ value: level.corpus_n.toLocaleString("en-US"), label: t("land.stat.corpus") });

  return (
    <Section id="open" heading={t("land.open.h")}>
      <p className="max-w-[62ch] text-lg text-muted">{t("land.open.b")}</p>
      {stats.length > 0 && (
        <dl className="mt-6 divide-y divide-rule border-y border-rule">
          {stats.map((s) => (
            <div key={s.label} className="flex items-baseline justify-between gap-6 py-3">
              <dt className="text-muted">{s.label}</dt>
              <dd className="num text-xl font-semibold">{s.value}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-6 flex flex-wrap gap-x-8 gap-y-2">
        <Link href="/lab" className="inline-flex h-11 items-center text-accent-ink underline underline-offset-4">
          {t("land.open.lab")}
        </Link>
        <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex h-11 items-center text-accent-ink underline underline-offset-4">
          {t("land.open.code")}
        </a>
      </p>
    </Section>
  );
}
