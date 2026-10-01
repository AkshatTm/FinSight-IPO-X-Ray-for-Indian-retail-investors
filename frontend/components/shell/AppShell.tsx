"use client";

import type { ReactNode } from "react";
import { useT } from "@/lib/useT";
import { ColdStartBanner } from "./ColdStartBanner";
import { Footer } from "./Footer";
import { NavBar } from "./NavBar";

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useT();
  return (
    <>
      <a
        href="#main"
        className="sr-only-keep focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-[6px] focus:bg-surface focus:px-3 focus:py-2"
      >
        {t("nav.skip")}
      </a>
      <NavBar />
      <ColdStartBanner />
      <main id="main" className="mx-auto w-full max-w-[1120px] flex-1 px-4 md:px-6">
        {children}
      </main>
      <Footer />
    </>
  );
}
