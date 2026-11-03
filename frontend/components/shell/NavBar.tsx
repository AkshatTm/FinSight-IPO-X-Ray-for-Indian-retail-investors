"use client";

import { List, X } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { StringKey } from "@/lib/copy";
import { useT } from "@/lib/useT";
import { AuthMenu } from "./AuthMenu";
import { HealthDot } from "./HealthDot";
import { ThemeToggle } from "./Toggles";

const LINKS: { href: string; key: StringKey }[] = [
  { href: "/ipos", key: "nav.ipos" },
  { href: "/how-it-works", key: "nav.how" },
  { href: "/lab", key: "nav.lab" },
  { href: "/about", key: "nav.about" },
];

function Wordmark() {
  return (
    <Link href="/" className="flex h-14 items-center text-xl font-semibold tracking-tight text-text">
      FinSight
    </Link>
  );
}

export function NavBar() {
  const { t } = useT();
  const path = usePathname();
  // The menu is open only for the route it was opened on, so navigating closes it.
  const [openFor, setOpenFor] = useState<string | null>(null);
  const open = openFor === path;
  const setOpen = (v: boolean | ((o: boolean) => boolean)) =>
    setOpenFor((cur) => ((typeof v === "function" ? v(cur === path) : v) ? path : null));
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpenFor(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const active = (href: string) => path === href || path.startsWith(`${href}/`);
  const link = (l: (typeof LINKS)[number]) => (
    <Link
      key={l.href}
      href={l.href}
      aria-current={active(l.href) ? "page" : undefined}
      className={`flex h-11 items-center px-3 text-sm ${
        active(l.href) ? "font-medium text-text underline decoration-stamp decoration-2 underline-offset-[10px]" : "text-muted hover:text-text"
      }`}
    >
      {t(l.key)}
    </Link>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-rule bg-bg px-4 md:px-6">
      <div className="mx-auto w-full max-w-[1120px]">
        <nav aria-label="Main" className="flex items-center justify-between gap-2">
          <Wordmark />
          <div className="hidden items-center md:flex">{LINKS.map(link)}</div>
          <div className="flex items-center gap-1">
            {path !== "/upload" && (
              <Link
                href="/upload"
                className="btn hidden h-11 items-center rounded-[6px] bg-stamp px-4 text-sm font-medium text-on-accent md:inline-flex"
              >
                {t("nav.analyse")}
              </Link>
            )}
            <AuthMenu />
            <span className="hidden md:inline-flex">
              <ThemeToggle />
            </span>
            <HealthDot />
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center md:hidden"
              aria-label={open ? t("nav.close") : t("nav.menu")}
              aria-expanded={open}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? <X size={22} /> : <List size={22} />}
            </button>
          </div>
        </nav>
      </div>
      {open && (
        <div className="mx-auto max-w-[1120px] border-t border-rule py-2 md:hidden">
          {LINKS.map(link)}
          <div className="flex items-center justify-between border-t border-rule pt-2">
            <ThemeToggle />
            {path !== "/upload" && (
              <Link href="/upload" className="btn inline-flex h-11 items-center rounded-[6px] bg-stamp px-4 text-sm font-medium text-on-accent">
                {t("nav.analyse")}
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
