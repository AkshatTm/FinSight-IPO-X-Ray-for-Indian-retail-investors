"use client";

import { useState } from "react";
import { FIELD_CONTENT, pick } from "@/lib/content/fields";
import type { StringKey } from "@/lib/i18n";
import { heatmap, ladderRows, ladderSize, ladderTakeaway, pct, type Cell } from "@/lib/lab";
import { useT } from "@/lib/useT";
import { LabFrame, Note } from "./LabFrame";

const label = (k: string) => `lab.rung.${k}` as StringKey;
const known = new Set(["rules", "qa_pretrained", "qa_finetuned", "bilstm_crf"]);

/** A bar for the share read correctly, with a thin whisker for the 95% range. */
function Bar({ cell, tone }: { cell: Cell; tone: string }) {
  const lo = pct(cell.lo);
  const hi = pct(cell.hi);
  return (
    <div aria-hidden className="relative mt-1.5 h-4">
      <div className={`absolute inset-y-0 left-0 rounded-[3px] ${tone}`} style={{ width: `${pct(cell.nvm)}%` }} />
      <div className="absolute top-1/2 h-px bg-[var(--text)]" style={{ left: `${lo}%`, width: `${hi - lo}%` }} />
      <div className="absolute top-[3px] h-2.5 w-px bg-[var(--text)]" style={{ left: `${lo}%` }} />
      <div className="absolute top-[3px] h-2.5 w-px bg-[var(--text)]" style={{ left: `${hi}%` }} />
    </div>
  );
}

export function LabMissing({ id, heading, shows }: { id: string; heading: string; shows: string }) {
  const { t } = useT();
  return (
    <LabFrame id={id} heading={heading} shows={shows}>
      <p className="text-muted">{t("lab.missing")}</p>
    </LabFrame>
  );
}

function Examples({
  heat,
  sel,
  onClose,
  name,
}: {
  heat: NonNullable<ReturnType<typeof heatmap>>;
  sel: { rung: string; field: string };
  onClose: () => void;
  name: (k: string) => string;
}) {
  const { t, lang } = useT();
  const list = heat.rows.find((r) => r.key === sel.rung)?.examples[sel.field] ?? [];
  const fact = FIELD_CONTENT[sel.field] ? pick(FIELD_CONTENT[sel.field].label, lang) : sel.field;
  return (
    <div className="mt-4 rounded-[10px] border border-rule bg-surface p-4" role="region" aria-live="polite">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold">{t("lab.fields.examples", { method: name(sel.rung), fact })}</h3>
        <button type="button" onClick={onClose} className="h-11 shrink-0 px-2 text-sm text-stamp underline underline-offset-2">
          {t("lab.fields.close")}
        </button>
      </div>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[30rem] text-left text-sm">
          <thead>
            <tr className="border-b border-rule text-muted">
              <th scope="col" className="py-2 pr-3 font-medium">IPO</th>
              <th scope="col" className="py-2 pr-3 font-medium">{t("lab.fields.read")}</th>
              <th scope="col" className="py-2 pr-3 font-medium">{t("lab.fields.checked")}</th>
              <th scope="col" className="py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {list.map((e, i) => (
              <tr key={`${e.ipo}-${i}`} className="border-b border-rule align-top last:border-0">
                <td className="py-2 pr-3 text-muted">{e.ipo.replace(/-20\d\d$/, "")}</td>
                <td className="py-2 pr-3 font-mono">{e.read || <span className="text-muted">{t("lab.fields.blank")}</span>}</td>
                <td className="py-2 pr-3 font-mono">{e.checked}</td>
                <td className="py-2">{e.correct ? t("lab.fields.right") : t("lab.fields.wrong")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function LabExtractor({ data }: { data: unknown }) {
  const { t, lang } = useT();
  const rows = ladderRows(data);
  const take = ladderTakeaway(data);
  const size = ladderSize(data);
  const heat = heatmap(data);
  const [sel, setSel] = useState<{ rung: string; field: string } | null>(null);
  if (!rows.length) return <LabMissing id="ladder" heading={t("lab.ladder.h")} shows={t("lab.ladder.shows")} />;
  const name = (r: { key: string; label: string }) => (known.has(r.key) ? t(label(r.key)) : r.label);

  return (
    <>
      <LabFrame id="ladder" heading={t("lab.ladder.h")} shows={t("lab.ladder.shows")}>
        <div className="overflow-x-auto rounded-[10px] border border-rule bg-surface">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <caption className="sr-only">{t("lab.chart.alt")}</caption>
            <thead>
              <tr className="border-b border-rule text-muted">
                <th scope="col" className="p-3 font-medium">{t("lab.col.method")}</th>
                <th scope="col" className="p-3 font-medium">{t("lab.col.whole")}</th>
                <th scope="col" className="p-3 font-medium">{t("lab.col.hidden")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-b border-rule align-top last:border-0">
                  <th scope="row" className="p-3 font-medium">
                    {name(r)}
                    {known.has(r.key) && (
                      <span className="mt-0.5 block font-normal text-muted">{t(`${label(r.key)}.d` as StringKey)}</span>
                    )}
                  </th>
                  <td className="w-[26%] p-3">
                    <span className="font-mono tabular-nums">{pct(r.full.nvm)}%</span>
                    <Bar cell={r.full} tone="bg-surface-2" />
                  </td>
                  <td className="w-[26%] p-3">
                    <span className="font-mono tabular-nums">{pct(r.body.nvm)}%</span>
                    <Bar cell={r.body} tone="bg-stamp/60" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {size && <Note>{t("lab.ladder.note", { n: size.n, k: size.k })}</Note>}
        {take && (
          <div className="mt-6 max-w-2xl rounded-[10px] border border-rule bg-surface-2 p-5">
            <h3 className="font-semibold">{t("lab.shows")}</h3>
            <p className="mt-2">{t("lab.ladder.take", { rules_body: take.rulesBody, ft_body: take.ftBody, delta: take.delta })}</p>
          </div>
        )}
      </LabFrame>
      {heat && (
        <LabFrame id="fields" heading={t("lab.fields.h")} shows={t("lab.fields.shows")}>
          <div className="overflow-x-auto rounded-[10px] border border-rule bg-surface">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <thead>
                <tr className="border-b border-rule text-muted">
                  <th scope="col" className="p-3 font-medium">{t("lab.fields.fact")}</th>
                  {heat.rows.map((r) => (
                    <th key={r.key} scope="col" className="p-3 font-medium">{known.has(r.key) ? t(label(r.key)) : r.key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heat.fields.map((f) => (
                  <tr key={f} className="border-b border-rule last:border-0">
                    <th scope="row" className="p-3 font-medium">{FIELD_CONTENT[f] ? pick(FIELD_CONTENT[f].label, lang) : f}</th>
                    {heat.rows.map((r) => {
                      const v = r.cells[f];
                      const bg = v === null ? undefined : { background: `color-mix(in srgb, var(--stamp) ${Math.round(v * 38)}%, var(--surface))` };
                      const on = sel?.rung === r.key && sel.field === f;
                      const has = (r.examples[f] ?? []).length > 0;
                      return (
                        <td key={r.key} className="p-0 font-mono tabular-nums" style={bg}>
                          {v === null ? (
                            <span className="block p-3">–</span>
                          ) : (
                            <button
                              type="button"
                              disabled={!has}
                              aria-pressed={on}
                              aria-label={`${known.has(r.key) ? t(label(r.key)) : r.key}, ${FIELD_CONTENT[f] ? pick(FIELD_CONTENT[f].label, lang) : f}: ${pct(v)}%`}
                              onClick={() => setSel(on ? null : { rung: r.key, field: f })}
                              className={`block min-h-11 w-full p-3 text-left disabled:cursor-default ${on ? "outline outline-2 -outline-offset-2 outline-[var(--stamp)]" : ""}`}
                            >
                              {pct(v)}%
                            </button>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Note>{t("lab.fields.note")} {t("lab.fields.click")}</Note>
          {sel && <Examples heat={heat} sel={sel} onClose={() => setSel(null)} name={(k) => (known.has(k) ? t(label(k)) : k)} />}
        </LabFrame>
      )}
    </>
  );
}
