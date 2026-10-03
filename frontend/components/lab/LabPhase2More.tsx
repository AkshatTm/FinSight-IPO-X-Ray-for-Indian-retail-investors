"use client";

import { formatPercent, formatRupee } from "@/lib/format";
import { STRINGS, type StringKey } from "@/lib/i18n";
import { outcomes, pct, rewrites, speedCost } from "@/lib/labB";
import { useT } from "@/lib/useT";
import { LabFrame, LabTable, Note, Stat } from "./LabFrame";

/** A label for a key the eval script wrote, or the key itself when there is no copy for it. */
function useLabel() {
  const { t } = useT();
  return (key: string, fallback: string) => (key in STRINGS ? t(key as StringKey) : fallback);
}

const signed = (x: number) => (x >= 0 ? `+${formatPercent(x * 100)}` : formatPercent(x * 100));

/** B05 §7.4 (E18–E20) with the honesty line. */
export function LabRewrites({ simplify, readability }: { simplify: unknown; readability: unknown }) {
  const { t } = useT();
  const label = useLabel();
  const r = rewrites(simplify, readability);
  if (!r) return null;
  const share = (k: number, n: number) => (n > 0 ? `${pct(k / n)}%` : "—");
  return (
    <LabFrame id="b-rewrites" heading={t("labb.rw.h")} shows={t("labb.rw.shows")}>
      {r.human.length > 0 && (
        <LabTable
          head={[t("labb.rw.col.system"), t("labb.rw.col.yes"), t("labb.rw.col.partly"), t("labb.rw.col.no")]}
          rows={r.human.map((h) => ({
            key: h.system,
            cells: [h.system, share(h.yes, h.n), share(h.partly, h.n), share(h.no, h.n)],
          }))}
        />
      )}
      <dl className="mt-8 grid gap-x-10 gap-y-8 sm:grid-cols-2">
        {r.gradeDrop !== null && (
          <Stat
            value={r.gradeDrop.toFixed(1)}
            label={t("labb.rw.grade")}
            sub={r.gradeBefore !== null && r.gradeAfter !== null ? t("labb.rw.gradeSub", { a: r.gradeBefore.toFixed(1), b: r.gradeAfter.toFixed(1) }) : undefined}
          />
        )}
        {r.rejected !== null && <Stat value={`${pct(r.rejected)}%`} label={t("labb.rw.rejected", { n: r.nChecked })} />}
      </dl>
      {r.reasons.length > 0 && (
        <ul className="mt-4 max-w-2xl space-y-1 text-sm text-muted">
          {r.reasons.map((x) => (
            <li key={x.key}>
              {label(`labb.rw.reason.${x.key}`, x.key)}: <span className="font-mono tabular-nums">{x.n}</span>
            </li>
          ))}
        </ul>
      )}
      <Note>{t("labb.rw.honest")}</Note>
    </LabFrame>
  );
}

/** B05 §7.6 (E21): always shown when the file exists, however weak the result. */
export function LabRiskLevelCheck({ data }: { data: unknown }) {
  const { t } = useT();
  const label = useLabel();
  const rows = outcomes(data);
  if (!rows.length) return null;
  return (
    <LabFrame id="b-risklevel" heading={t("labb.rl.h")} shows={t("labb.rl.shows")}>
      {rows.map((o) => {
        const outcome = label(`labb.rl.outcome.${o.key}`, o.key.replaceAll("_", " "));
        return (
          <div key={o.key} className="mt-6 first:mt-0">
            <p className="text-lg font-medium">{t(`labb.rl.verdict.${o.strength}`, { outcome })}</p>
            <p className="mt-1 text-sm text-muted">
              {t("labb.rl.rho", { rho: o.rho.toFixed(2), lo: o.lo.toFixed(2), hi: o.hi.toFixed(2), n: o.n })}
            </p>
            {o.boxes.length > 0 && (
              <div className="mt-4">
                <LabTable
                  head={[t("labb.rl.col.level"), t("labb.rl.col.n"), t("labb.rl.col.median"), t("labb.rl.col.range")]}
                  rows={o.boxes.map((b) => ({
                    key: b.level,
                    cells: [b.level, String(b.n), signed(b.median), `${signed(b.p25)} … ${signed(b.p75)}`],
                  }))}
                />
              </div>
            )}
          </div>
        );
      })}
      <Note>{t("labb.rl.note")}</Note>
    </LabFrame>
  );
}

/** B05 §7.7 (E23, E24). */
export function LabSpeedCost({ latency, cost }: { latency: unknown; cost: unknown }) {
  const { t } = useT();
  const s = speedCost(latency, cost);
  if (!s) return null;
  return (
    <LabFrame id="b-speed" heading={t("labb.sc.h")} shows={t("labb.sc.shows")}>
      {s.stages.length > 0 && (
        <>
          <LabTable
            head={[t("labb.sc.col.stage"), t("labb.sc.col.p50"), t("labb.sc.col.p95")]}
            rows={s.stages.map((x) => ({ key: x.stage, cells: [x.stage, x.p50.toFixed(1), x.p95.toFixed(1)] }))}
          />
          {s.nDocs > 0 && <Note>{t("labb.sc.docs", { n: s.nDocs })}</Note>}
        </>
      )}
      <dl className="mt-8 grid gap-x-10 gap-y-8 sm:grid-cols-3">
        {s.perPage !== null && <Stat value={s.perPage.toFixed(2)} label={t("labb.sc.perPage")} />}
        {s.inrMean !== null && (
          <Stat
            value={formatRupee(s.inrMean.toFixed(2))}
            label={t("labb.sc.cost")}
            sub={s.inrMax !== null ? t("labb.sc.costMax", { max: formatRupee(s.inrMax.toFixed(2)) }) : undefined}
          />
        )}
        {s.freeShare !== null && <Stat value={formatPercent(s.freeShare * 100)} label={t("labb.sc.free")} />}
      </dl>
    </LabFrame>
  );
}
