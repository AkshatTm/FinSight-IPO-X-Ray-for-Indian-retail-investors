"use client";

import { MarkIcon } from "@/components/facts/VerdictMark";
import { Drawer } from "@/components/ui/Drawer";
import { comparison, reasonText } from "@/lib/chat";
import { useChat } from "@/lib/chatStore";
import { useUi } from "@/lib/store";
import { useLayout } from "@/lib/useBreakpoint";
import { useT } from "@/lib/useT";
import { docLabel } from "./common";

/** Right-side drawer (full-screen sheet on phones) for one checked number (spec 7.6). */
export function EvidenceDrawer({ ipoId }: { ipoId: string }) {
  const { t, lang } = useT();
  const layout = useLayout();
  const ref = useChat((s) => s.evidence);
  const turns = useChat((s) => s.turns[ipoId]);
  const close = useChat((s) => s.closeEvidence);
  const setHighlight = useUi((s) => s.setHighlight);

  const open = !!ref && ref.ipoId === ipoId;
  const turn = turns?.find((x) => x.id === ref?.turnId);
  const v = turn?.verdicts.find((x) => x.index === ref?.index);
  if (!open || !turn || !v) return null;

  const ev = v.evidence;
  const cmp = comparison(v, lang);
  const passage = [...(turn.retrieval?.passages ?? []), ...(turn.retrieval?.dropped ?? [])].find((p) => p.id === ev?.passage_id);
  const needle = ev?.value && "raw" in ev.value ? ev.value.raw : "";
  const at = passage && needle ? passage.snippet.indexOf(needle) : -1;

  const row = (label: string, pair: [string, string] | null) =>
    pair && (
      <tr>
        <th scope="row" className="py-1.5 pr-3 text-left font-normal text-muted">{label}</th>
        <td className="py-1.5 pr-3 font-mono text-sm">{pair[0]}</td>
        <td className="py-1.5 font-mono text-sm">{pair[1]}</td>
      </tr>
    );

  return (
    <Drawer title={t(`evidence.title.${v.status}`)} icon={<MarkIcon state={v.status} size={20} />} onClose={close}>
        <table className="mt-4 w-full">
          <thead>
            <tr className="text-left text-xs text-muted">
              <td />
              <th scope="col" className="pb-1 font-normal">{t("ev.inAnswer")}</th>
              <th scope="col" className="pb-1 font-normal">{t("ev.inDoc")}</th>
            </tr>
          </thead>
          <tbody>
            {row(t("ev.asWritten"), cmp.asWritten[1] || cmp.asWritten[0] ? cmp.asWritten : null)}
            {row(t("ev.inCrore"), cmp.crore)}
            {row(t("ev.inMillion"), cmp.million)}
          </tbody>
        </table>

        <h3 className="mt-5 text-sm font-semibold">{t("ev.reason")}</h3>
        <p className="mt-1 text-sm">{reasonText(v, lang)}</p>

        {ev && (
          <>
            <h3 className="mt-5 text-sm font-semibold">{t("ev.source")}</h3>
            <p className="mt-1 text-sm text-muted">{t("ev.sourceLine", { doc: docLabel(ev.doc, ev.page, lang).split(" ")[0], page: ev.page })}</p>
            {passage && (
              <p className="mt-2 line-clamp-6 rounded-[6px] bg-surface-2 p-3 font-mono text-xs leading-relaxed">
                {at >= 0 ? (
                  <>
                    {passage.snippet.slice(0, at)}
                    <mark className="bg-transparent text-text underline decoration-2 underline-offset-2" style={{ textDecorationColor: v.status === "verified" ? "var(--ok)" : v.status === "contradicted" ? "var(--bad)" : "var(--query)" }}>
                      {needle}
                    </mark>
                    {passage.snippet.slice(at + needle.length)}
                  </>
                ) : (
                  passage.snippet
                )}
              </p>
            )}
            <button
              type="button"
              onClick={() => {
                setHighlight({ ipoId, doc: ev.doc, page: ev.page, bbox: ev.bbox, kind: v.status });
                if (layout !== "wide") close();
              }}
              className="mt-4 h-11 self-start rounded-[6px] border border-rule bg-surface-2 px-4 text-sm font-medium hover:border-stamp"
            >
              {t("common.showInDocument")}
            </button>
          </>
        )}

        <p className="mt-auto pt-6 text-xs text-muted">{t("ev.foot")}</p>
    </Drawer>
  );
}
