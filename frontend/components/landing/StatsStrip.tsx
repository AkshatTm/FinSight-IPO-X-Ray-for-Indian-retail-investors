"use client";

import Link from "next/link";
import { MiniBars, MiniLine, MiniMeter } from "@/components/charts/Mini";
import { useIpos } from "@/lib/api/hooks";
import { SCORECARD } from "@/lib/scorecard";
import { useT } from "@/lib/useT";

/**
 * Four real numbers under the hero. IPO and page counts come from the API; the two accuracies are
 * the re-measured values in eval_results/final/FINAL_SCORECARD.md (see lib/scorecard.ts).
 */
export function StatsStrip() {
  const { t } = useT();
  const { data: ipos } = useIpos();
  const sorted = [...(ipos ?? [])].sort((a, b) => (a.listing_date ?? "").localeCompare(b.listing_date ?? ""));
  const pages = sorted.map((i) => i.rhp_pages).filter((n) => n > 0);
  const totalPages = pages.reduce((a, b) => a + b, 0);
  const cumulative = pages.map((_, i) => pages.slice(0, i + 1).reduce((a, b) => a + b, 0));

  const tiles: { value: string; label: string; viz: React.ReactNode; note?: string }[] = [];
  if (sorted.length) {
    tiles.push({
      value: String(sorted.length),
      label: t("land.stat.ipos"),
      viz: <MiniBars values={sorted.map((i) => Number(i.issue_size_inr ?? 0))} label={t("land.stat.ipos.viz")} />,
      note: t("land.stat.ipos.note"),
    });
  }
  if (totalPages) {
    tiles.push({
      value: totalPages.toLocaleString("en-US"),
      label: t("land.stat.pages"),
      viz: <MiniLine values={cumulative} label={t("land.stat.pages.viz")} />,
    });
  }
  tiles.push({
    value: `${Math.round(SCORECARD.factsNvm * 100)}%`,
    label: t("land.stat.facts"),
    viz: <MiniMeter value={SCORECARD.factsNvm * 100} label={t("land.stat.facts")} />,
    note: t("land.stat.facts.note"),
  });
  tiles.push({
    value: `${Math.round(SCORECARD.redflagStatus * 100)}%`,
    label: t("land.stat.flags"),
    viz: <MiniMeter value={SCORECARD.redflagStatus * 100} label={t("land.stat.flags")} tone="var(--chart-2)" />,
    note: t("land.stat.flags.note"),
  });

  return (
    <section aria-label={t("land.open.h")} className="border-b border-rule bg-surface">
      <div className="mx-auto max-w-[1200px] px-5 py-8 md:px-8">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4">
          {tiles.map((s) => (
            <div key={s.label} className="min-w-0 lg:border-l lg:border-rule lg:pl-6 lg:first:border-l-0 lg:first:pl-0">
              <dd className="num text-3xl font-bold tracking-tight md:text-4xl">{s.value}</dd>
              <dt className="mt-1 text-base text-muted">{s.label}</dt>
              <div className="mt-3">{s.viz}</div>
              {s.note && <p className="mt-2 text-sm text-muted">{s.note}</p>}
            </div>
          ))}
        </dl>
        <p className="mt-6 text-sm text-muted">
          {t("land.stat.source")}{" "}
          <Link href="/lab" className="text-accent-ink underline underline-offset-4">
            {t("land.open.lab")}
          </Link>
        </p>
      </div>
    </section>
  );
}
