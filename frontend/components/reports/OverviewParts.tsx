"use client";

import type { StringKey } from "@/lib/copy";
import { DOC_SHORT_KEY } from "@/lib/doc";
import type { Unit } from "@/lib/format";
import { anchorFor, flagTitleKey, offerLine, statusKey, type FlagStatus, type OfferLineParams, type ReportOverview } from "@/lib/report";
import { byPeriod, cell, type Sod } from "@/lib/sod";
import { useT } from "@/lib/useT";
import { StatusIcon } from "./StatusIcon";

export function SectionTitle({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="font-serif text-xl font-semibold tracking-tight">
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
      <div className="mt-3 flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <p>
          <span className="block text-sm text-muted">{t("ov.promoterPre")}</span>
          <span className="num font-serif text-3xl font-semibold">{pre.text ?? t("fin.notStated")}</span>
        </p>
        <span aria-hidden className="text-2xl text-muted">→</span>
        <p>
          <span className="block text-sm text-muted">{t("ov.promoterPost")}</span>
          {post.text ? (
            <span className="num font-serif text-3xl font-semibold">{post.text}</span>
          ) : (
            <span className="text-muted">{t("ov.promoterPostNone")}</span>
          )}
        </p>
      </div>
      {pre.page ? <p className="mt-2 text-xs text-muted">{t("ov.page", { p: pre.page })}</p> : null}
    </section>
  );
}

const ALL_FLAGS = Array.from({ length: 13 }, (_, i) => `RF${String(i + 1).padStart(2, "0")}`);

/** Red flags in three clearly separate groups: decided, not available, pending (not calculated). */
export function FlagsGlance({ flags, onGo }: { flags: { id: string; status: FlagStatus }[]; onGo: (hash: string) => void }) {
  const { t } = useT();
  const known = new Map(flags.map((f) => [f.id, f.status]));
  const decided = flags.filter((f) => f.status === "ok" || f.status === "watch" || f.status === "concern");
  const na = flags.filter((f) => f.status === "not_available" || f.status === "not_applicable");
  const pending = flags.length === 0 ? [] : ALL_FLAGS.filter((id) => !known.has(id));
  const title = (id: string) => (flagTitleKey(id) ? t(flagTitleKey(id) as StringKey) : id);
  const group = (heading: string, hint: string | null, body: React.ReactNode) => (
    <div className="py-3 first:pt-0 last:pb-0">
      <h3 className="text-sm font-semibold">{heading}</h3>
      {hint && <p className="text-xs text-muted">{hint}</p>}
      <div className="mt-2">{body}</div>
    </div>
  );
  if (flags.length === 0) return <p className="mt-3 text-sm text-muted">{t("rep.notReady")}</p>;
  return (
    <div className="mt-3 divide-y divide-rule border-y border-rule py-3">
      {decided.length > 0 &&
        group(
          t("ov.flagsDecided"),
          null,
          <ul className="grid gap-x-8 gap-y-1.5 sm:grid-cols-2">
            {decided.map((f) => (
              <li key={f.id}>
                <button type="button" onClick={() => onGo(`#${anchorFor("redflag", f.id)}`)} className="flex w-full items-center gap-2 text-left text-sm hover:text-stamp">
                  <StatusIcon status={f.status} size={16} />
                  <span className="min-w-0 flex-1">{title(f.id)}</span>
                  <span className="text-xs text-muted">{t(statusKey(f.status))}</span>
                </button>
              </li>
            ))}
          </ul>,
        )}
      {na.length > 0 &&
        group(
          t("ov.flagsNA"),
          t("ov.flagsNAHint"),
          <p className="text-sm text-muted">{na.map((f) => title(f.id)).join(", ")}</p>,
        )}
      {pending.length > 0 &&
        group(
          t("ov.flagsPending"),
          t("ov.flagsPendingHint"),
          <p className="text-sm text-muted">{pending.map(title).join(", ")}</p>,
        )}
    </div>
  );
}
