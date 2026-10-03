"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
import { anchorFor, FLAG_FILTERS, filterKey, flagMatches, flagSentence, flagTitleKey, sortFlags, statusKey, type FlagFilter, type RedFlag } from "@/lib/report";
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
  return (
    <section aria-labelledby="rf-title" className="space-y-5">
      <header>
        <h2 id="rf-title" className="text-xl font-semibold">{t("rf.title")}</h2>
        <p className="mt-1 text-sm text-muted">{t("rf.sub")}</p>
      </header>
      <div role="group" aria-label={t("rf.title")} className="flex flex-wrap gap-2">
        {FLAG_FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3 py-1 text-sm ${filter === f ? "border-stamp bg-stamp/10 font-medium" : "border-rule hover:bg-surface-2"}`}
          >
            {t(filterKey(f))} <span className="text-muted">{f === "all" ? flags.length : flags.filter((x) => flagMatches(x, f)).length}</span>
          </button>
        ))}
      </div>
      <ul className="space-y-3">
        {shown.map((f) => (
          <FlagCard key={f.id} flag={f} onShowPage={onShowPage} />
        ))}
      </ul>
    </section>
  );
}

function FlagCard({ flag, onShowPage }: { flag: RedFlag; onShowPage?: (page: number) => void }) {
  const { t } = useT();
  const titleKey = flagTitleKey(flag.id);
  const sentence = flagSentence(flag);
  const numbers = Object.entries(flag.numbers_used ?? {});
  const evidence = flag.evidence ?? [];
  return (
    <li id={anchorFor("redflag", flag.id)} className="scroll-mt-24 rounded-[10px] border border-rule bg-surface p-4" data-status={flag.status}>
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
                    <button type="button" className="rounded-full border border-rule px-2 text-xs" onClick={() => onShowPage(evidence[i].page)}>
                      {t("rf.page", { p: evidence[i].page })}
                    </button>
                  ) : (
                    <span className="rounded-full border border-rule px-2 text-xs text-muted">{t("rf.page", { p: evidence[i].page })}</span>
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
        <button type="button" className="mt-3 rounded-full border border-rule px-3 py-1 text-sm hover:bg-surface-2" onClick={() => onShowPage(evidence[0].page)}>
          {t("rf.show")}
        </button>
      )}
    </li>
  );
}

