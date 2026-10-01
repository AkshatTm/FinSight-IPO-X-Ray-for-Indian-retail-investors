"use client";

import { useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import { useT } from "@/lib/useT";

interface Props {
  panes: ReactNode[];
  /** Starting sizes in percent; must add up to 100. */
  initial: number[];
  /** Minimum widths in px, one per pane (spec 7.1: 300 / 420 / 320). */
  minPx: number[];
}

/** Clamp a boundary drag so both neighbours keep their minimum width. */
export function resizePair(
  sizes: number[],
  i: number,
  deltaPct: number,
  containerPx: number,
  minPx: number[],
): number[] {
  const minA = (minPx[i] / containerPx) * 100;
  const minB = (minPx[i + 1] / containerPx) * 100;
  const total = sizes[i] + sizes[i + 1];
  const a = Math.min(total - minB, Math.max(minA, sizes[i] + deltaPct));
  const next = [...sizes];
  next[i] = a;
  next[i + 1] = total - a;
  return next;
}

export function ResizablePanes({ panes, initial, minPx }: Props) {
  const { t } = useT();
  const ref = useRef<HTMLDivElement>(null);
  const [sizes, setSizes] = useState(initial);
  const start = (i: number) => (e: PointerEvent) => {
    e.preventDefault();
    const x0 = e.clientX;
    const base = sizes;
    function move(ev: globalThis.PointerEvent) {
      const w = ref.current?.getBoundingClientRect().width;
      if (w) setSizes(resizePair(base, i, ((ev.clientX - x0) / w) * 100, w, minPx));
    }
    function up() {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const onKey = (i: number) => (e: KeyboardEvent) => {
    const w = ref.current?.getBoundingClientRect().width;
    if (!w || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    e.preventDefault();
    setSizes((s) => resizePair(s, i, e.key === "ArrowLeft" ? -2 : 2, w, minPx));
  };

  return (
    <div ref={ref} className="flex h-full min-h-0 w-full">
      {panes.map((pane, i) => (
        <div key={i} className="flex min-h-0 min-w-0" style={{ width: `${sizes[i]}%` }}>
          <div className="min-h-0 min-w-0 flex-1 overflow-hidden">{pane}</div>
          {i < panes.length - 1 && (
            <div
              role="separator"
              aria-orientation="vertical"
              aria-label={t("ws.resize")}
              aria-valuenow={Math.round(sizes[i])}
              aria-valuemin={0}
              aria-valuemax={100}
              tabIndex={0}
              onPointerDown={start(i)}
              onKeyDown={onKey(i)}
              className="group relative w-3 shrink-0 cursor-col-resize touch-none"
            >
              <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-rule group-hover:bg-stamp group-focus-visible:bg-stamp" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
