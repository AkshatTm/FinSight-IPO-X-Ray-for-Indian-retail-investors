"use client";

import type { Schemas } from "@/lib/api/client";
import { errorMessage } from "@/lib/i18n";
import { useChat } from "@/lib/chatStore";
import { guardKind, type Turn } from "@/lib/chat";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { docLabel } from "./common";

const card = "rounded-[10px] border p-4 text-sm";
const chip = "h-11 rounded-full border border-rule px-4 text-left hover:border-stamp";

function Facts({ ipoId, facts }: { ipoId: string; facts: Schemas["FactSummary"][] }) {
  const { lang } = useT();
  const setHighlight = useUi((s) => s.setHighlight);
  return (
    <ul className="mt-3 divide-y divide-rule border-y border-rule">
      {facts.slice(0, 4).map((f) => (
        <li key={f.field_id}>
          <button
            type="button"
            onClick={() => setHighlight({ ipoId, doc: f.doc, page: f.page, bbox: null, kind: "source" })}
            className="flex min-h-11 w-full items-center justify-between gap-3 px-1 py-2 text-left hover:bg-surface-2"
          >
            <span className="text-muted">{lang === "hi" ? f.label_hi : f.label_en}</span>
            <span className="flex items-center gap-2">
              <span className="font-medium">{f.display}</span>
              <span className="rounded-full border border-rule px-2 py-0.5 text-xs text-muted">{docLabel(f.doc, f.page, lang)}</span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Advice, forecast and privacy cards (spec 13.3). Never implies a decision. */
export function GuardCard({ turn }: { turn: Turn }) {
  const { t, lang } = useT();
  const ask = useChat((s) => s.ask);
  const openGlossary = useUi((s) => s.openGlossary);
  const g = turn.guard!;
  const kind = guardKind(g.reason);
  return (
    <div className={`${card} border-rule bg-surface`} role="note">
      <h3 className="text-base font-semibold">{t(`guard.${kind}.title` as "guard.advice.title")}</h3>
      <p className="mt-1 text-muted">{t(`guard.${kind}.body` as "guard.advice.body")}</p>
      {kind === "advice" && g.facts.length > 0 && (
        <>
          <Facts ipoId={turn.ipoId} facts={g.facts} />
          <p className="mt-3">
            <button type="button" className="inline-flex h-11 items-center text-stamp underline underline-offset-2" onClick={() => openGlossary("sebi")}>
              {t("guard.advice.sebi")}
            </button>
          </p>
        </>
      )}
      {kind === "forecast" && (
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className={chip} onClick={() => ask(turn.ipoId, t("guard.forecast.chipMoney"), lang, "chip")}>
            {t("guard.forecast.chipMoney")}
          </button>
          <button type="button" className={chip} onClick={() => ask(turn.ipoId, t("ask.pastRevenue"), lang, "chip")}>
            {t("guard.forecast.chipPast")}
          </button>
        </div>
      )}
    </div>
  );
}

export function AbstainCard({ turn, suggestions }: { turn: Turn; suggestions: string[] }) {
  const { t, lang } = useT();
  const ask = useChat((s) => s.ask);
  const setHighlight = useUi((s) => s.setHighlight);
  const p = turn.abstain?.closest_passage ?? null;
  return (
    <div className={`${card} border-query bg-surface`} role="note">
      <h3 className="text-base font-semibold">{t("abstain.title")}</h3>
      <p className="mt-1 text-muted">{t("abstain.body")}</p>
      {p && (
        <div className="mt-3 rounded-[6px] bg-surface-2 p-3">
          <p className="mb-1 font-medium">{docLabel(p.doc, p.page_start, lang)}</p>
          <p className="line-clamp-3 text-muted">{p.snippet}</p>
          <button
            type="button"
            onClick={() => setHighlight({ ipoId: turn.ipoId, doc: p.doc, page: p.page_start, bbox: null, kind: "source" })}
            className="mt-2 h-11 text-stamp underline underline-offset-2"
          >
            {t("common.showInDocument")}
          </button>
        </div>
      )}
      {suggestions.length > 0 && (
        <>
          <p className="mt-3 text-muted">{t("abstain.tryDifferent")}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {suggestions.slice(0, 3).map((q) => (
              <button key={q} type="button" className={chip} onClick={() => ask(turn.ipoId, q, lang, "chip")}>
                {q}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export function ErrorCard({ turn }: { turn: Turn }) {
  const { t, lang } = useT();
  const ask = useChat((s) => s.ask);
  return (
    <div className={`${card} border-rule bg-surface`} role="alert">
      <h3 className="text-base font-semibold">{t("error.title")}</h3>
      <p className="mt-1 text-muted">{errorMessage(turn.error?.code, lang)}</p>
      <button type="button" className={`${chip} mt-3`} onClick={() => ask(turn.ipoId, turn.question, turn.language, "typed")}>
        {t("error.retry")}
      </button>
    </div>
  );
}
