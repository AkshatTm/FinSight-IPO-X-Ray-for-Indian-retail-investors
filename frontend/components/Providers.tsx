"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { useUi } from "@/lib/store";
import { USE_MOCKS } from "@/lib/api/client";

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
  });
}

declare global {
  interface Window {
    /** Test hook (dev and mock builds only): lets Playwright drive the highlight mechanism. */
    __fsUi?: typeof useUi;
  }
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(makeClient);
  const [ready, setReady] = useState(!USE_MOCKS);
  const lang = useUi((s) => s.lang);
  const theme = useUi((s) => s.theme);

  // Restore saved preferences after mount so server and first client render agree.
  useEffect(() => {
    let saved = false;
    try {
      saved = !!localStorage.getItem("fs_ui");
    } catch {
      /* storage blocked: defaults apply */
    }
    void Promise.resolve(useUi.persist.rehydrate()).then(() => {
      if (!saved) useUi.getState().setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
    });
  }, []);

  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || USE_MOCKS) window.__fsUi = useUi;
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === "hi" ? "hi" : "en";
  }, [lang]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (!USE_MOCKS) return;
    let cancelled = false;
    void import("@/mocks/browser").then(({ startMocks }) =>
      startMocks().then(() => {
        if (!cancelled) setReady(true);
      }),
    );
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) return null;
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
