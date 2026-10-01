"use client";

import { useEffect, useRef } from "react";
import { useSuggested } from "@/lib/api/hooks";
import { useChat } from "@/lib/chatStore";
import type { StringKey } from "@/lib/i18n";
import { useT } from "@/lib/useT";
import { answerLanguage } from "@/lib/voice";
import { Composer } from "./Composer";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { TurnView } from "./TurnView";

const FALLBACK: StringKey[] = ["ask.chip.money", "ask.chip.use", "ask.chip.promoters", "ask.chip.price", "ask.chip.ofs"];

export function AskPane({ ipoId, company }: { ipoId: string; company: string }) {
  const { t, lang } = useT();
  const turns = useChat((s) => s.turns[ipoId]) ?? [];
  const ask = useChat((s) => s.ask);
  const { data } = useSuggested(ipoId);
  const scroller = useRef<HTMLDivElement>(null);
  const streaming = turns.some((x) => x.status === "streaming");

  const suggested = (data ?? []).slice(0, 6).map((s) => s.text);
  const chips = suggested.length ? suggested : FALLBACK.map((k) => t(k));
  const tail = turns[turns.length - 1];
  const progress = `${turns.length}:${tail?.streamed.length ?? 0}:${tail?.verdicts.length ?? 0}:${tail?.status}`;

  // Follow the answer as it streams.
  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [progress]);

  return (
    <section data-pane="ask" aria-label={t("ws.tab.ask")} className="flex h-full min-h-0 flex-col">
      <header className="px-4 pb-2 pt-4">
        <h2 className="text-lg font-semibold">{t("ask.title", { company })}</h2>
      </header>
      <div ref={scroller} className="min-h-0 flex-1 space-y-6 overflow-y-auto px-4 pb-4" aria-live="off">
        {turns.length === 0 ? (
          <div className="space-y-4 pt-2">
            <p className="text-muted">{t("ask.empty")}</p>
            <div className="flex flex-col items-start gap-2">
              {chips.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => void ask(ipoId, q, lang, "chip")}
                  className="min-h-11 rounded-[10px] border border-rule bg-surface px-3 py-2 text-left text-sm hover:border-stamp"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          turns.map((turn) => <TurnView key={turn.id} turn={turn} suggestions={chips} />)
        )}
      </div>
      <Composer
        ipoId={ipoId}
        disabled={streaming}
        onSend={(q, voice) => void ask(ipoId, q, voice ? answerLanguage(q, lang) : lang, voice ? "voice" : "typed")}
      />
      <EvidenceDrawer ipoId={ipoId} />
    </section>
  );
}
