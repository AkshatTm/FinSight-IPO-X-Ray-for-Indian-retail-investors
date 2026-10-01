"use client";

import { useLayoutEffect, useState, useSyncExternalStore } from "react";
import { useT } from "@/lib/useT";

export const TOUR_KEY = "fs_tour_workspace";

const STEPS = [
  { pane: "facts", text: "tour.1" },
  { pane: "document", text: "tour.2" },
  { pane: "ask", text: "tour.3" },
] as const;

function seen(): boolean {
  try {
    return localStorage.getItem(TOUR_KEY) === "1";
  } catch {
    return true;
  }
}

function markSeen() {
  try {
    localStorage.setItem(TOUR_KEY, "1");
  } catch {
    // Storage blocked: the tour simply shows again next visit.
  }
}

/** First-visit coach marks, three steps, never in demo mode (spec 7.9). */
export function Tour({ ready }: { ready: boolean }) {
  const { t } = useT();
  const [step, setStep] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const eligible = useSyncExternalStore(
    () => () => {},
    () => new URLSearchParams(window.location.search).get("demo") !== "1" && !seen(),
    () => false,
  );
  const active = ready && eligible && !dismissed;

  useLayoutEffect(() => {
    if (!active) return;
    const measure = () => {
      const el = document.querySelector(`[data-pane="${STEPS[step].pane}"]`);
      setRect(el && el.getBoundingClientRect().width > 0 ? el.getBoundingClientRect() : null);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [active, step]);

  if (!active) return null;
  const finish = () => {
    markSeen();
    setDismissed(true);
  };
  const last = step === STEPS.length - 1;
  const vw = typeof window === "undefined" ? 1366 : window.innerWidth;
  const vh = typeof window === "undefined" ? 768 : window.innerHeight;
  const cardW = Math.min(300, vw - 32);
  // Card sits inside the highlighted pane near its top; falls back to bottom-centre when the pane is hidden.
  const left = rect ? Math.min(Math.max(16, rect.left + 16), vw - cardW - 16) : (vw - cardW) / 2;
  const top = rect ? Math.min(Math.max(80, rect.top + 56), vh - 190) : vh - 190;

  return (
    <div className="fixed inset-0 z-[60]" role="presentation">
      {rect && (
        <div
          aria-hidden
          className="pointer-events-none fixed rounded-[10px] border-2 border-stamp"
          style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }}
        />
      )}
      <div
        role="dialog"
        aria-label={t(STEPS[step].text)}
        className="fixed rounded-[10px] border border-rule bg-surface p-4 shadow-[var(--shadow-float)]"
        style={{ left, top, width: cardW }}
        onKeyDown={(e) => e.key === "Escape" && finish()}
      >
        <p>{t(STEPS[step].text)}</p>
        <div className="mt-3 flex items-center justify-between">
          <button type="button" onClick={finish} className="h-11 text-sm text-muted underline underline-offset-2">
            {t("tour.skip")}
          </button>
          <button
            type="button"
            autoFocus
            onClick={() => (last ? finish() : setStep(step + 1))}
            className="h-11 rounded-[6px] bg-stamp px-4 text-sm font-medium text-bg"
          >
            {last ? t("tour.done") : t("tour.next")}
          </button>
        </div>
      </div>
    </div>
  );
}
