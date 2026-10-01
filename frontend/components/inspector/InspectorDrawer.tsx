"use client";

import { useState, type ReactNode } from "react";
import { VerdictMark } from "@/components/facts/VerdictMark";
import { Drawer } from "@/components/ui/Drawer";
import { useTrace } from "@/lib/api/hooks";
import type { Schemas } from "@/lib/api/client";
import { useChat } from "@/lib/chatStore";
import type { Turn } from "@/lib/chat";
import { formatMoney } from "@/lib/format";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";

type Passage = Schemas["RetrievedPassage"];

function Section({ title, open, children }: { title: string; open?: boolean; children: ReactNode }) {
  return (
    <details open={open} className="border-b border-rule py-3">
      <summary className="flex min-h-11 cursor-pointer items-center font-semibold">{title}</summary>
      <div className="pt-2">{children}</div>
    </details>
  );
}

const th = "px-2 py-1.5 text-left text-xs font-normal text-muted";
const td = "px-2 py-1.5 align-top text-sm";

function PassageRows({ rows, dim }: { rows: Passage[]; dim?: boolean }) {
  const { t } = useT();
  return (
    <>
      {rows.map((p) => (
        <tr key={p.id} className={`border-t border-rule ${dim ? "text-muted" : ""}`}>
          <td className={td}>{p.n}</td>
          <td className={td}>{t(p.doc === "rhp" ? "doc.rhpShort" : "doc.prospectusShort")}</td>
          <td className={td}>{p.page_start}</td>
          <td className={td}>{p.section}</td>
          <td className={td}>{p.bm25_rank ?? "—"}</td>
          <td className={td}>{p.dense_rank ?? "—"}</td>
          <td className={td}>{p.fused_rank ?? "—"}</td>
          <td className={`${td} font-mono`}>{p.rerank_score != null ? p.rerank_score.toFixed(2) : "—"}</td>
        </tr>
      ))}
    </>
  );
}

function Body({ turn }: { turn: Turn }) {
  const { t, lang } = useT();
  const { data: trace, isPending } = useTrace(turn.final?.trace_id, true);
  const timings = Object.entries(turn.final?.timings_ms ?? {});
  const max = Math.max(1, ...timings.map(([, ms]) => ms));
  const passages = turn.retrieval?.passages ?? [];
  const dropped = turn.retrieval?.dropped ?? [];
  const answer = turn.answer?.text ?? "";

  return (
    <div className="mt-2">
      <Section title={t("insp.steps")} open>
        <ol className="space-y-2">
          {timings.map(([name, ms]) => (
            <li key={name} className="text-sm">
              <div className="flex justify-between">
                <span>{t(`stage.${name}` as "stage.guard")}</span>
                <span className="font-mono">{t("insp.ms", { ms })}</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-surface-2">
                <div className="h-full rounded-full bg-stamp" style={{ width: `${Math.max(2, (ms / max) * 100)}%` }} />
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section title={t("insp.pages")} open>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[34rem]">
            <thead>
              <tr>
                <th className={th}>{t("insp.col.n")}</th>
                <th className={th}>{t("insp.col.doc")}</th>
                <th className={th}>{t("insp.col.page")}</th>
                <th className={th}>{t("insp.col.section")}</th>
                <th className={th} title={t("insp.help.bm25")}>{t("insp.col.bm25")}</th>
                <th className={th} title={t("insp.help.dense")}>{t("insp.col.dense")}</th>
                <th className={th}>{t("insp.col.fused")}</th>
                <th className={th} title={t("insp.help.score")}>{t("insp.col.score")}</th>
              </tr>
            </thead>
            <tbody>
              <PassageRows rows={passages} />
              {dropped.length > 0 && (
                <>
                  <tr>
                    <td colSpan={8} className="pt-3 text-xs text-muted">{t("insp.dropped")}</td>
                  </tr>
                  <PassageRows rows={dropped} dim />
                </>
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-muted">
          {t("insp.col.bm25")}: {t("insp.help.bm25")}. {t("insp.col.dense")}: {t("insp.help.dense")}. {t("insp.col.score")}: {t("insp.help.score")}.
        </p>
      </Section>

      <Section title={t("insp.checks")}>
        {turn.verdicts.length === 0 ? (
          <p className="text-sm text-muted">{t("meter.none")}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[34rem]">
              <thead>
                <tr>
                  <th className={th}>{t("insp.col.number")}</th>
                  <th className={th}>{t("insp.col.written")}</th>
                  <th className={th}>{t("insp.col.inr")}</th>
                  <th className={th}>{t("insp.col.found")}</th>
                  <th className={th}>{t("insp.col.rule")}</th>
                  <th className={th}>{t("insp.col.result")}</th>
                </tr>
              </thead>
              <tbody>
                {turn.verdicts.map((v) => {
                  const a = v.answer_value;
                  const ev = v.evidence?.value;
                  return (
                    <tr key={v.index} className="border-t border-rule">
                      <td className={td}>{v.index + 1}</td>
                      <td className={`${td} font-mono`}>{answer.slice(v.answer_char_span[0], v.answer_char_span[1]) || ("raw" in a ? a.raw : "")}</td>
                      <td className={`${td} font-mono`}>{a.kind === "money" && a.value_inr ? formatMoney(a.value_inr, "full", lang) : "—"}</td>
                      <td className={`${td} font-mono`}>{ev && "raw" in ev ? ev.raw : "—"}</td>
                      <td className={`${td} font-mono text-xs`}>{v.reason_code}</td>
                      <td className={td}><VerdictMark state={v.status} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title={t("insp.prompt")}>
        {isPending ? (
          <div className="skeleton h-24" aria-busy="true" aria-label={t("insp.loading")} />
        ) : (
          <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-[6px] bg-surface-2 p-3 font-mono text-xs">{trace?.prompt}</pre>
        )}
      </Section>
    </div>
  );
}

/** "How this answer was made": timeline, pages read, number checks, prompt (spec 7.7). */
export function InspectorDrawer({ ipoId }: { ipoId: string }) {
  const { t } = useT();
  const open = useUi((s) => s.inspector);
  const setOpen = useUi((s) => s.setInspector);
  const turns = useChat((s) => s.turns[ipoId]) ?? [];
  const [, force] = useState(0);
  if (!open) return null;
  const turn = [...turns].reverse().find((x) => x.final);
  return (
    <Drawer title={t("insp.title")} onClose={() => (setOpen(false), force((n) => n + 1))} widthClass="sm:w-[640px]">
      {turn ? <Body turn={turn} /> : <p className="mt-6 text-muted">{t("insp.empty")}</p>}
    </Drawer>
  );
}
