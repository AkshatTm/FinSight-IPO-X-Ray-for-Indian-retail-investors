"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { Lang, Unit } from "@/lib/format";

export type Theme = "light" | "dark";

/** The one highlight mechanism: set it here, the document viewer reacts. */
export interface Highlight {
  ipoId: string;
  doc: "rhp" | "prospectus";
  page: number;
  /** [x0, y0, x1, y1] in page points; omit to only jump to the page. */
  bbox?: [number, number, number, number] | null;
  /** "source" = stamp blue; verdicts use the verdict colour (evidence drawer). */
  kind: "source" | "verified" | "unverifiable" | "contradicted";
  /** Increments so clicking the same fact twice replays the animation. */
  nonce: number;
}

/** Which page of which document the viewer shows. Reset when the IPO changes. */
export interface DocView {
  ipoId: string;
  doc: "rhp" | "prospectus";
  page: number;
}

interface UiState {
  lang: Lang;
  theme: Theme;
  unit: Unit;
  highlight: Highlight | null;
  view: DocView | null;
  coldBannerDismissed: boolean;
  setLang: (l: Lang) => void;
  setTheme: (t: Theme) => void;
  setUnit: (u: Unit) => void;
  setHighlight: (h: Omit<Highlight, "nonce"> | null) => void;
  setView: (v: DocView) => void;
  dismissColdBanner: () => void;
}

let nonce = 0;

export const useUi = create<UiState>()(
  persist(
    (set) => ({
      lang: "en",
      theme: "light",
      unit: "crore",
      highlight: null,
      view: null,
      coldBannerDismissed: false,
      setLang: (lang) => set({ lang }),
      setTheme: (theme) => set({ theme }),
      setUnit: (unit) => set({ unit }),
      // One mechanism: a highlight also moves the viewer to its page.
      setHighlight: (h) =>
        set(
          h
            ? { highlight: { ...h, nonce: ++nonce }, view: { ipoId: h.ipoId, doc: h.doc, page: h.page } }
            : { highlight: null },
        ),
      setView: (view) => set({ view }),
      dismissColdBanner: () => set({ coldBannerDismissed: true }),
    }),
    {
      name: "fs_ui",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ lang: s.lang, theme: s.theme, unit: s.unit }),
      // Rehydrated from Providers after mount, so server and first client render match.
      skipHydration: true,
    },
  ),
);
