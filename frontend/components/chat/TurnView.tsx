"use client";

import { useEffect, useState } from "react";
import { useToast } from "@/lib/toast";
import { copyText, meterText, type Turn } from "@/lib/chat";
import { useT } from "@/lib/useT";
import { AnswerText } from "./AnswerText";
import { AbstainCard, ErrorCard, GuardCard } from "./Cards";

/** One line that follows the pipeline; the elapsed seconds appear after 5 s (spec 7.5.3). */
function StageLine({ turn }: { turn: Turn }) {
  const { t } = useT();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!turn.stage) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [turn.stage]);
  if (!turn.stage) return null;
  const s = Math.floor((now - turn.stage.startedAt) / 1000);
  const key = turn.stage.name === "done" ? "generating" : turn.stage.name;
  return (
    <p role="status" className="text-sm text-muted">
      {t(`stage.${key}`)}
      {s >= 5 && ` · ${s}s`}
    </p>
  );
}

export function TurnView({ turn, suggestions }: { turn: Turn; suggestions: string[] }) {
  const { t, lang } = useT();
  const toast = useToast((s) => s.show);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText(turn));
      toast(t("toast.copied"));
    } catch {
      /* clipboard blocked: nothing to confirm */
    }
  };

  const body = turn.error ? (
    <ErrorCard turn={turn} />
  ) : turn.guard?.blocked ? (
    <GuardCard turn={turn} />
  ) : turn.abstain ? (
    <AbstainCard turn={turn} suggestions={suggestions} />
  ) : turn.streamed || turn.answer ? (
    <div className="space-y-2">
      <AnswerText turn={turn} />
      {turn.answer && turn.final && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-rule pt-2 text-sm">
          <p className="text-muted">{meterText(turn.verdicts, lang)}</p>
          <button type="button" onClick={copy} className="h-11 rounded-[6px] px-3 text-stamp hover:bg-surface-2">
            {t("ask.copy")}
          </button>
        </div>
      )}
    </div>
  ) : null;

  return (
    <article className="space-y-3" aria-label={turn.question}>
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-[10px] bg-stamp/10 px-3 py-2" lang={turn.language === "hi" ? "hi" : "en"}>
          <span className="sr-only-keep">{t("ask.you")}: </span>
          {turn.question}
        </p>
      </div>
      <StageLine turn={turn} />
      {body}
    </article>
  );
}
