"use client";

import { useSyncExternalStore } from "react";

export type Layout = "wide" | "mid" | "narrow";

const WIDE = "(min-width: 1280px)";
const MID = "(min-width: 1024px)";

function subscribe(cb: () => void) {
  const a = window.matchMedia(WIDE);
  const b = window.matchMedia(MID);
  a.addEventListener("change", cb);
  b.addEventListener("change", cb);
  return () => {
    a.removeEventListener("change", cb);
    b.removeEventListener("change", cb);
  };
}

const snapshot = (): Layout =>
  window.matchMedia(WIDE).matches ? "wide" : window.matchMedia(MID).matches ? "mid" : "narrow";

/** Workspace layout (spec 7.1): three panes >= 1280, two panes 1024-1279, tabs below 1024. */
export function useLayout(): Layout {
  return useSyncExternalStore(subscribe, snapshot, () => "wide");
}
