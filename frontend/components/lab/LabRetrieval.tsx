"use client";

import type { StringKey } from "@/lib/copy";
import { pct, retrievalRows } from "@/lib/lab";
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
