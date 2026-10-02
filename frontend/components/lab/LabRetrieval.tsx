"use client";

import type { StringKey } from "@/lib/i18n";
import { asrStats, pct, retrievalRows } from "@/lib/lab";
import { useT } from "@/lib/useT";
import { LabFrame, Note } from "./LabFrame";

export function LabRetrieval({ data }: { data: unknown }) {
  const { t } = useT();
  const rows = retrievalRows(data);
  if (!rows.length) return null;
  return (
    <LabFrame id="retrieval" heading={t("lab.ret.h")} shows={t("lab.ret.shows")}>
      <div className="max-w-3xl overflow-x-auto rounded-[10px] border border-rule bg-surface">
        <table className="w-full min-w-[30rem] text-left text-sm">
          <thead>
            <tr className="border-b border-rule text-muted">
              <th scope="col" className="p-3 font-medium">{t("lab.ret.col.method")}</th>
              <th scope="col" className="p-3 font-medium">{t("lab.ret.col.recall")}</th>
              <th scope="col" className="p-3 font-medium">{t("lab.ret.col.abstain")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-b border-rule last:border-0">
                <th scope="row" className="p-3 font-medium">{t(`lab.ret.${r.key}` as StringKey)}</th>
                <td className="p-3 font-mono tabular-nums">{pct(r.recall5)}%</td>
                <td className="p-3 font-mono tabular-nums">{r.abstained ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>{t("lab.ret.note")}</Note>
    </LabFrame>
  );
}

export function LabHindi({ asr, retrieval }: { asr: unknown; retrieval: unknown }) {
  const { t } = useT();
  const a = asrStats(asr);
  const hi = retrievalRows(retrieval).find((r) => r.key === "hybrid+rerank")?.hiRecall5 ?? null;
  if (!a && hi === null) return null;
  return (
    <LabFrame id="hindi" heading={t("lab.hi.h")} shows={t("lab.hi.shows")}>
      <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-2">
        {a && (
          <div>
            <dd className="text-4xl font-semibold tabular-nums tracking-tight">{a.cer}%</dd>
            <dt className="mt-2 text-muted">{t("lab.hi.cer", { n: a.clips })}</dt>
            <p className="mt-1 text-sm text-muted">{t("lab.hi.refs")}</p>
          </div>
        )}
        {hi !== null && (
          <div>
            <dd className="text-4xl font-semibold tabular-nums tracking-tight">{pct(hi)}%</dd>
            <dt className="mt-2 text-muted">{t("lab.hi.retrieval")}</dt>
          </div>
        )}
      </dl>
      <Note>{t("lab.hi.line")}</Note>
    </LabFrame>
  );
}
