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

interface UiState {
  lang: Lang;
  theme: Theme;
  unit: Unit;
  highlight: Highlight | null;
  coldBannerDismissed: boolean;
  setLang: (l: Lang) => void;
  setTheme: (t: Theme) => void;
  setUnit: (u: Unit) => void;
  setHighlight: (h: Omit<Highlight, "nonce"> | null) => void;
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
      coldBannerDismissed: false,
      setLang: (lang) => set({ lang }),
      setTheme: (theme) => set({ theme }),
      setUnit: (unit) => set({ unit }),
      setHighlight: (h) => set({ highlight: h ? { ...h, nonce: ++nonce } : null }),
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
