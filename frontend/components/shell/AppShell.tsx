"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { DemoMode } from "@/components/demo/DemoMode";
import { ToastHost } from "@/components/ui/ToastHost";
import { useT } from "@/lib/useT";
import { ColdStartBanner } from "./ColdStartBanner";
import { Footer } from "./Footer";
import { NavBar } from "./NavBar";

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useT();
  // The workspace (/ipos/<id>) uses the full width for three panes.
  const wide = /^\/ipos\/[^/]+/.test(usePathname());
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
      <main id="main" className={`mx-auto w-full flex-1 px-4 md:px-6 ${wide ? "max-w-[1760px]" : "max-w-[1120px]"}`}>
        {children}
      </main>
      <Footer />
      <ToastHost />
      <DemoMode />
    </>
  );
}
