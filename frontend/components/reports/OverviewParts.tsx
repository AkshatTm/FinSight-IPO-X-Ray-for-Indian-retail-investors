"use client";

import type { StringKey } from "@/lib/copy";
import { DOC_SHORT_KEY } from "@/lib/doc";
import type { Unit } from "@/lib/format";
import { offerLine, type FlagStatus, type OfferLineParams, type ReportOverview } from "@/lib/report";
import { byPeriod, cell, type Sod } from "@/lib/sod";
import { useT } from "@/lib/useT";
import { FlagGrid, ShareholdingChart } from "./ReportCharts";

export function SectionTitle({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-xl font-semibold tracking-tight">
      {children}
    </h2>
  );
}

/** Key facts: the document, the offer in one line, and the latest-year figures when the summary has them. */
export function KeyFacts({ report, sod, unit }: { report: ReportOverview; sod: Sod | null; unit: Unit }) {
  const { t } = useT();
  const doc = report.doc;
  const offer = offerLine(report.offer_line_params as OfferLineParams | null);
  const latest = (key: string, perShare = false) => cell(byPeriod(sod?.financials[key]).fy.latest ?? null, unit, perShare);
  const rows: { label: string; value: string; page?: number | null }[] = [];
  if (doc.doc_type) rows.push({ label: t("ov.kf.document"), value: t(DOC_SHORT_KEY[doc.doc_type]) });
  if (doc.pages) rows.push({ label: t("ov.kf.pages"), value: t("rep.pages", { n: doc.pages }) });
  for (const [key, label] of [
    ["revenue", "ov.kf.revenue"],
    ["profit_after_tax", "ov.kf.pat"],
    ["net_worth", "ov.kf.networth"],
    ["total_borrowings", "ov.kf.debt"],
  ] as const) {
    const c = latest(key);
    if (c.text) rows.push({ label: t(label), value: c.text, page: c.page });
  }
  if (rows.length === 0 && !offer) return null;
  return (
    <section aria-labelledby="ov-facts">
      <SectionTitle id="ov-facts">{t("ov.keyFacts")}</SectionTitle>
      {offer && <p className="mt-3 max-w-[62ch] text-lg">{t(offer.key as StringKey, offer.vars)}</p>}
      <dl className="mt-4 divide-y divide-rule border-y border-rule">
        {rows.map((r) => (
          <div key={r.label} className="flex items-baseline justify-between gap-6 py-2.5">
            <dt className="text-muted">{r.label}</dt>
            <dd className="num text-right font-medium">
              {r.value}
              {r.page ? <span className="ml-2 whitespace-nowrap text-xs font-normal text-muted">{t("ov.page", { p: r.page })}</span> : null}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** The issuer's own "Our Strengths" list. Hidden when the document gave none. */
export function Strengths({ sod }: { sod: Sod | null }) {
  const { t } = useT();
  if (!sod || sod.strengths.length === 0) return null;
  return (
    <section aria-labelledby="ov-strengths" className="rounded-[10px] border border-rule bg-surface p-5">
      <SectionTitle id="ov-strengths">{t("ov.strengths")}</SectionTitle>
      <p className="mt-1 text-sm text-muted">{t("ov.strengthsNote")}</p>
      <ul className="mt-4 divide-y divide-rule">
        {sod.strengths.map((s) => (
          <li key={s.heading + s.sentence} className="py-3 first:pt-0 last:pb-0">
            <p className="font-medium">{s.heading}</p>
            {s.sentence && <p className="mt-1 text-sm text-muted">{s.sentence}</p>}
            {s.page ? <p className="mt-1 text-xs text-muted">{t("ov.page", { p: s.page })}</p> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Promoter holding, before then after the offer. "After" is usually unknown until the price is set. */
export function PromoterHolding({ sod }: { sod: Sod | null }) {
  const { t } = useT();
  const pre = cell(sod?.promoter_holding_pre, "crore");
  const post = cell(sod?.promoter_holding_post, "crore");
  if (!pre.text && !post.text) return null;
  return (
    <section aria-labelledby="ov-promoter">
      <SectionTitle id="ov-promoter">{t("ov.promoter")}</SectionTitle>
      <div className="mt-3 flex flex-wrap items-baseline gap-x-8 gap-y-1">
        <p>
          <span className="block text-sm text-muted">{t("ov.promoterPre")}</span>
          <span className="num text-3xl font-bold">{pre.text ?? t("fin.notStated")}</span>
        </p>
        <span aria-hidden className="text-2xl text-muted">→</span>
        <p>
          <span className="block text-sm text-muted">{t("ov.promoterPost")}</span>
          {post.text ? <span className="num text-3xl font-bold">{post.text}</span> : <span className="text-base text-muted">{t("ov.promoterPostNone")}</span>}
        </p>
      </div>
      <div className="mt-3"><ShareholdingChart pre={pre.n} post={post.n} /></div>
      {pre.page ? <p className="mt-2 text-xs text-muted">{t("ov.page", { p: pre.page })}</p> : null}
    </section>
  );
}

/** Red flags in three clearly separate groups: decided, not available, pending (not calculated). */
export function FlagsGlance({ flags, onGo }: { flags: { id: string; status: FlagStatus }[]; onGo: (hash: string) => void }) {
  const { t } = useT();
  if (flags.length === 0) return <p className="mt-3 text-sm text-muted">{t("rep.notReady")}</p>;
  return (
    <div className="mt-3">
      <FlagGrid flags={flags} onGo={onGo} />
    </div>
  );
}
