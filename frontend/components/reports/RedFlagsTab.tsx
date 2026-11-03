"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
import { anchorFor, FLAG_FILTERS, filterKey, flagMatches, flagSentence, flagTitleKey, sortFlags, statusKey, type FlagFilter, type RedFlag } from "@/lib/report";
import type { StringKey } from "@/lib/copy";
import { useT } from "@/lib/useT";
import { StatusIcon } from "./StatusIcon";

/** Red flags tab (B05 §5.4): filter chips and one card per check. */
/** `onShowPage` is absent until uploads have a Document view: pages then show as plain text. */
export function RedFlagsTab({ docId, onShowPage }: { docId: string; onShowPage?: (page: number) => void }) {
  const { t } = useT();
  const [filter, setFilter] = useState<FlagFilter>("all");
  const q = useQuery({
    queryKey: ["redflags", docId],
    queryFn: () => apiGet<Schemas["RedFlags"]>(`/api/docs/${docId}/redflags`),
  });
  if (q.isPending) return <div aria-busy className="h-48 animate-pulse rounded-[10px] bg-surface-2 motion-reduce:animate-none" />;
  if (q.isError) return <ErrorBlock error={q.error} onRetry={() => void q.refetch()} />;
  const flags = sortFlags(q.data.flags ?? []);
  const shown = flags.filter((f) => flagMatches(f, filter));
  const severe = q.data.severe_overrides ?? [];
  return (
    <section aria-labelledby="rf-title" className="space-y-5">
      <header>
        <h2 id="rf-title" className="font-serif text-xl font-semibold tracking-tight">{t("rf.title")}</h2>
        <p className="mt-1 text-sm text-muted">{t("rf.sub")}</p>
      </header>
      {severe.length > 0 && (
        <div className="rounded-[10px] border border-rule bg-surface p-4" data-testid="severe-overrides">
          <h3 className="font-semibold">{t("rf.severe.h")}</h3>
          <p className="mt-1 text-sm text-muted">{t("rf.severe.sub")}</p>
          <ul className="mt-3 space-y-3">
            {severe.map((o) => (
              <li key={o.id} id={anchorFor("override", o.id)} className="scroll-mt-40 text-sm">
                <p className="font-medium">{o.title}</p>
                {o.about && o.about !== "issuer" && <p className="mt-0.5 text-xs text-muted">{t(`rf.about.${o.about}` as StringKey)}</p>}
                <p className="mt-1">{o.sentence}</p>
                {o.evidence?.page != null && (
                  <span className="mt-1 inline-block rounded-[4px] border border-rule px-1.5 text-xs text-muted">{t("rf.page", { p: o.evidence.page })}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div role="group" aria-label={t("rf.title")} className="flex flex-wrap gap-2">
        {FLAG_FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className={`rounded-[6px] border px-3 py-1 text-sm ${filter === f ? "border-stamp bg-stamp/10 font-medium" : "border-rule hover:bg-surface-2"}`}
          >
            {t(filterKey(f))} <span className="text-muted">{f === "all" ? flags.length : flags.filter((x) => flagMatches(x, f)).length}</span>
          </button>
        ))}
      </div>
      <FlagGroups flags={shown} all={flags} filter={filter} onShowPage={onShowPage} />
    </section>
  );
}

const ALL_IDS = Array.from({ length: 13 }, (_, i) => "RF" + String(i + 1).padStart(2, "0"));

/** Decided, not available and pending are separate groups so a missing number never reads as "OK". */
function FlagGroups({ flags, all, filter, onShowPage }: { flags: RedFlag[]; all: RedFlag[]; filter: FlagFilter; onShowPage?: (page: number) => void }) {
  const { t } = useT();
  const decided = flags.filter((f) => f.status === "ok" || f.status === "watch" || f.status === "concern");
  const na = flags.filter((f) => f.status === "not_available" || f.status === "not_applicable");
  const have = new Set(all.map((f) => f.id));
  const pending = all.length > 0 && (filter === "all" || filter === "na") ? ALL_IDS.filter((id) => !have.has(id)) : [];
  if (decided.length + na.length + pending.length === 0) return <p className="text-sm text-muted">{t("rk.none")}</p>;
  const heading = (h: string, hint: string) => (
    <div className="mt-8 first:mt-0">
      <h3 className="text-sm font-semibold">{h}</h3>
      <p className="text-xs text-muted">{hint}</p>
    </div>
  );
  return (
    <div>
      {decided.length > 0 && (
        <ul className="divide-y divide-rule border-y border-rule">
          {decided.map((f) => <FlagCard key={f.id} flag={f} onShowPage={onShowPage} />)}
        </ul>
      )}
      {na.length > 0 && (
        <>
          {heading(t("rf.group.na"), t("rf.group.naHint"))}
          <ul className="mt-2 divide-y divide-rule border-y border-rule">
            {na.map((f) => <FlagCard key={f.id} flag={f} onShowPage={onShowPage} />)}
          </ul>
        </>
      )}
      {pending.length > 0 && (
        <>
          {heading(t("rf.group.pending"), t("rf.group.pendingHint"))}
          <ul className="mt-2 divide-y divide-rule border-y border-rule">
            {pending.map((id) => (
              <li key={id} id={anchorFor("redflag", id)} className="scroll-mt-40 flex items-baseline justify-between gap-4 py-3 text-sm">
                <span>{flagTitleKey(id) ? t(flagTitleKey(id) as StringKey) : id}</span>
                <span className="text-muted">{t("rf.pendingLine")}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function FlagCard({ flag, onShowPage }: { flag: RedFlag; onShowPage?: (page: number) => void }) {
  const { t } = useT();
  const titleKey = flagTitleKey(flag.id);
  const sentence = flagSentence(flag);
  const numbers = Object.entries(flag.numbers_used ?? {});
  const evidence = flag.evidence ?? [];
  return (
    <li id={anchorFor("redflag", flag.id)} className="scroll-mt-40 py-4" data-status={flag.status}>
      <div className="flex items-start gap-2">
        <StatusIcon status={flag.status} />
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold">
            {titleKey ? t(titleKey) : flag.title} <span className="ml-1 text-sm font-normal text-muted">{t(statusKey(flag.status))}</span>
          </h3>
          <p className="mt-1 text-sm">{sentence === "rf.missing" ? t("rf.missing") : sentence}</p>
        </div>
      </div>
      {numbers.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer">{t("rf.numbers")}</summary>
          <ul className="mt-2 space-y-1">
            {numbers.map(([name, value], i) => (
              <li key={name} className="flex flex-wrap items-center gap-2">
                <span className="text-muted">{name}</span>
                <span className="tabular-nums">{value}</span>
                {evidence[i] &&
                  (onShowPage ? (
                    <button type="button" className="rounded-[4px] border border-rule px-1.5 text-xs" onClick={() => onShowPage(evidence[i].page)}>
                      {t("rf.page", { p: evidence[i].page })}
                    </button>
                  ) : (
                    <span className="rounded-[4px] border border-rule px-1.5 text-xs text-muted">{t("rf.page", { p: evidence[i].page })}</span>
                  ))}
              </li>
            ))}
          </ul>
        </details>
      )}
      {flag.rule && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer">{t("rf.how")}</summary>
          <p className="mt-2 text-muted">{flag.rule}</p>
        </details>
      )}
      {evidence[0] && onShowPage && (
        <button type="button" className="mt-3 rounded-[6px] border border-rule px-3 py-1 text-sm hover:bg-surface-2" onClick={() => onShowPage(evidence[0].page)}>
          {t("rf.show")}
        </button>
      )}
    </li>
  );
}
