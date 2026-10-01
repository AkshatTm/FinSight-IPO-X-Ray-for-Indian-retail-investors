"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { MarkIcon } from "@/components/facts/VerdictMark";
import { segmentAnswer, type Turn, type Verdict } from "@/lib/chat";
import { useChat } from "@/lib/chatStore";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { docLabel } from "./common";

const subscribeMotion = (cb: () => void) => {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
};
export const useReducedMotion = () =>
  useSyncExternalStore(subscribeMotion, () => window.matchMedia("(prefers-reduced-motion: reduce)").matches, () => false);

/** Verdicts reveal one by one, 120 ms apart (spec 7.5.4); all at once under reduced motion. */
function useStaggeredReveal(verdicts: Verdict[], reduced: boolean): Set<number> {
  const [shown, setShown] = useState<Set<number>>(new Set());
  const scheduled = useRef(new Map<number, number>());
  const lastAt = useRef(0);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    for (const v of verdicts) {
      if (scheduled.current.has(v.index)) continue;
      const now = performance.now();
      const at = reduced ? now : Math.max(now, lastAt.current + 120);
      lastAt.current = at;
      scheduled.current.set(v.index, at);
      timers.push(setTimeout(() => setShown((s) => new Set(s).add(v.index)), Math.max(0, at - now)));
    }
    // Timers are left to fire even if verdicts change; they only add indexes.
    return undefined;
  }, [verdicts, reduced]);

  return shown;
}

/** A thin line in the verdict colour from the mark toward the document pane edge (spec 7.5.4). */
function LeaderLine({ from, color }: { from: HTMLElement; color: string }) {
  const [geo, setGeo] = useState<{ x1: number; y1: number; x2: number; len: number } | null>(null);
  useEffect(() => {
    const pane = document.querySelector<HTMLElement>('[data-pane="document"]');
    if (!pane) return;
    const m = from.getBoundingClientRect();
    const p = pane.getBoundingClientRect();
    if (p.width === 0) return;
    const x1 = m.left;
    const x2 = Math.min(p.right - 6, x1 - 8);
    const timer = setTimeout(() => setGeo({ x1, y1: m.top + m.height / 2, x2, len: Math.abs(x1 - x2) }), 0);
    const gone = setTimeout(() => setGeo(null), 1300);
    return () => {
      clearTimeout(timer);
      clearTimeout(gone);
    };
  }, [from]);
  if (!geo) return null;
  return createPortal(
    <svg aria-hidden className="pointer-events-none fixed inset-0 z-30 h-screen w-screen">
      <line
        className="leader"
        x1={geo.x1} y1={geo.y1} x2={geo.x2} y2={geo.y1}
        stroke={color} strokeWidth={1}
        style={{ ["--len" as string]: geo.len }}
      />
    </svg>,
    document.body,
  );
}

function Mark({ v, text, shown, turn, onOpen }: { v: Verdict; text: string; shown: boolean; turn: Turn; onOpen: (el: HTMLElement) => void }) {
  const { t } = useT();
  const view = useUi((s) => s.view);
  const [el, setEl] = useState<HTMLButtonElement | null>(null);
  const color = v.status === "verified" ? "var(--ok)" : v.status === "contradicted" ? "var(--bad)" : "var(--query)";
  const ev = v.evidence;
  const visible = !!ev && view?.ipoId === turn.ipoId && view.doc === ev.doc && view.page === ev.page;
  const word = t(`verdict.${v.status}`);
  return (
    // The slot is always rendered so the line never reflows when the mark lands.
    <span className="inline-block w-[1.4em] align-text-bottom" style={{ textAlign: "center" }}>
      {shown && (
        <button
          ref={setEl}
          type="button"
          title={word}
          aria-label={`${word}. ${t("mark.open", { value: text })}`}
          onClick={(e) => onOpen(e.currentTarget)}
          className="mark-in inline-flex h-[1.4em] w-[1.4em] items-center justify-center"
        >
          <MarkIcon state={v.status} size={16} />
          <span className="sr-only-keep">{word}</span>
        </button>
      )}
      {shown && visible && el && <LeaderLine from={el} color={color} />}
    </span>
  );
}

export function AnswerText({ turn }: { turn: Turn }) {
  const { t, lang } = useT();
  const reduced = useReducedMotion();
  const openEvidence = useChat((s) => s.openEvidence);
  const setHighlight = useUi((s) => s.setHighlight);
  const shown = useStaggeredReveal(turn.verdicts, reduced);

  if (!turn.answer) {
    return <p className={`whitespace-pre-wrap ${turn.status === "streaming" ? "caret" : ""}`}>{turn.streamed}</p>;
  }
  const segs = segmentAnswer(turn.answer.text, turn.verdicts, turn.answer.citations);
  const passages = turn.retrieval?.passages ?? [];

  return (
    <p className="whitespace-pre-wrap" lang={turn.language === "hi" ? "hi" : "en"}>
      {segs.map((s, i) => {
        if (s.type === "text") return <span key={i}>{s.text}</span>;
        if (s.type === "number") {
          const v = s.verdict;
          return (
            <span key={i} className="whitespace-nowrap">
              <span className="underline decoration-muted/60 decoration-1 underline-offset-[3px]">{s.text}</span>
              <Mark v={v} text={s.text} shown={shown.has(v.index)} turn={turn} onOpen={() => openEvidence({ ipoId: turn.ipoId, turnId: turn.id, index: v.index })} />
            </span>
          );
        }
        const p = passages.find((x) => x.n === s.n);
        return (
          <span key={i} className="group relative inline-block">
            <button
              type="button"
              aria-label={t("cite.jump", { n: s.n })}
              onClick={() => p && setHighlight({ ipoId: turn.ipoId, doc: p.doc, page: p.page_start, bbox: null, kind: "source" })}
              className="mx-0.5 rounded-[4px] border border-rule bg-surface-2 px-1 text-xs font-medium text-stamp hover:border-stamp"
            >
              {s.text}
            </button>
            {p && (
              <span role="tooltip" className="pointer-events-none absolute bottom-full left-0 z-20 mb-1 hidden w-64 rounded-[10px] border border-rule bg-surface p-2 text-xs shadow-[var(--shadow-float)] group-focus-within:block group-hover:block">
                <span className="mb-1 block font-medium">{docLabel(p.doc, p.page_start, lang)}</span>
                <span className="line-clamp-3 block text-muted">{p.snippet}</span>
              </span>
            )}
          </span>
        );
      })}
    </p>
  );
}
