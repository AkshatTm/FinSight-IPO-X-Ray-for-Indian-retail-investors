"use client";

import type { StringKey } from "@/lib/i18n";
import { verifierStats, weakStats } from "@/lib/lab";
import { useT } from "@/lib/useT";
import { LabFrame, Note } from "./LabFrame";

function Stat({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <div>
      <dd className="text-4xl font-semibold tabular-nums tracking-tight">{value}</dd>
      <dt className="mt-2 text-muted">{label}</dt>
      {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
    </div>
  );
}

const fmt = (n: number) => n.toLocaleString("en-IN");

export function LabWeak({ data }: { data: unknown }) {
  const { t } = useT();
  const w = weakStats(data);
  if (!w) return null;
  return (
    <LabFrame id="weak" heading={t("lab.weak.h")} shows={t("lab.weak.shows")}>
      <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-3">
        <Stat value={fmt(w.examples)} label={t("lab.weak.examples")} />
        <Stat value={fmt(w.ipos)} label={t("lab.weak.ipos")} />
        <Stat value={`${w.precision}%`} label={t("lab.weak.precision")} sub={t("lab.weak.range", { lo: w.lo, hi: w.hi })} />
      </dl>
      <Note>{t("lab.weak.note")}</Note>
    </LabFrame>
  );
}

export function LabVerifier({ data }: { data: unknown }) {
  const { t } = useT();
  const v = verifierStats(data);
  if (!v) return null;
  return (
    <LabFrame id="verifier" heading={t("lab.ver.h")} shows={t("lab.ver.shows")}>
      <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-3">
        <Stat value={`${v.caught.hits}/${v.caught.n}`} label={t("lab.ver.caught")} />
        {v.falseAlarms && <Stat value={`${v.falseAlarms.hits}/${v.falseAlarms.n}`} label={t("lab.ver.false")} />}
        {v.unit && (
          <Stat
            value={`${v.unit.hits}/${v.unit.n}`}
            label={t("lab.ver.unit")}
            sub={v.unitFixed ? t("lab.ver.unitFix", { hits: v.unitFixed.hits, n: v.unitFixed.n }) : undefined}
          />
        )}
      </dl>
      {v.types.length > 0 && (
        <div className="mt-8 max-w-xl overflow-x-auto rounded-[10px] border border-rule bg-surface">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-rule text-muted">
                <th scope="col" className="p-3 font-medium">{t("lab.ver.col.type")}</th>
                <th scope="col" className="p-3 font-medium">{t("lab.ver.col.n")}</th>
                <th scope="col" className="p-3 font-medium">{t("lab.ver.col.ok")}</th>
              </tr>
            </thead>
            <tbody>
              {v.types.map((r) => (
                <tr key={r.key} className="border-b border-rule last:border-0">
                  <th scope="row" className="p-3 font-medium">{t(`lab.ver.type.${r.key}` as StringKey)}</th>
                  <td className="p-3 font-mono tabular-nums">{r.n}</td>
                  <td className="p-3 font-mono tabular-nums">{r.ok}/{r.n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Note>{t("lab.ver.note")}</Note>
    </LabFrame>
  );
}
