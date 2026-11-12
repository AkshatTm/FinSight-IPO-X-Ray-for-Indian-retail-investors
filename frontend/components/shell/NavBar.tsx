"use client";

import { List, X } from "@phosphor-icons/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type CSSProperties } from "react";
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

/** Over the charcoal hero the bar borrows the band's colours, so children keep using text/muted/rule. */
const BAND_TOKENS = {
  "--text": "var(--on-band)",
  "--text-muted": "var(--on-band-muted)",
  "--rule": "rgba(255, 255, 255, 0.08)",
} as CSSProperties;

/** A page with a saffron read-line across it: the product in one glyph. */
function Logomark() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden focusable="false" className="shrink-0">
      <path d="M5 2.75h8.2L17.25 6.8V19.25H5z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M13 2.75V7h4.25" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M7.75 10.5h6.5M7.75 16h4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.45" />
      <path d="M2.5 13.25h17" stroke="var(--stamp)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function Wordmark() {
  return (
    <Link href="/" className="flex h-14 items-center gap-2 text-lg font-semibold tracking-[-0.02em] text-text">
      <Logomark />
      FinSight
    </Link>
  );
}

/** True while the home page's hero is still under the bar. */
function useOverHero(home: boolean): boolean {
  const [over, setOver] = useState(true);
  useEffect(() => {
    if (!home) return;
    const hero = document.querySelector("main section");
    const update = () => setOver(!hero || hero.getBoundingClientRect().bottom > 56);
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [home]);
  return home && over;
}

export function NavBar() {
  const { t } = useT();
  const path = usePathname();
  const band = useOverHero(path === "/");
  // The menu is open only for the route it was opened on, so navigating closes it.
  const [openFor, setOpenFor] = useState<string | null>(null);
  const open = openFor === path;
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
      className={`relative flex h-11 items-center px-3 text-sm transition-colors duration-150 ${
        active(l.href)
          ? "font-medium text-text after:absolute after:inset-x-3 after:bottom-[9px] after:h-[2px] after:rounded-full after:bg-stamp"
          : "text-muted hover:text-text"
      }`}
    >
      {t(l.key)}
    </Link>
  );
  const cta = path !== "/upload" && (
    <Link
      href="/upload"
      className={`inline-flex h-10 items-center rounded-[8px] px-4 text-sm font-medium transition-[background-color,transform] duration-150 active:scale-[0.97] ${
        band ? "bg-white/10 text-on-band ring-1 ring-white/15 hover:bg-white/16" : "bg-text text-bg hover:opacity-90"
      }`}
    >
      {t("nav.analyse")}
    </Link>
  );

  return (
    <header
      style={band ? BAND_TOKENS : undefined}
      className={`sticky top-0 z-40 border-b px-4 transition-[background-color,border-color] duration-200 md:px-0 ${
        band ? "border-transparent bg-band" : "border-rule bg-bg/85 backdrop-blur-md supports-[not(backdrop-filter:blur(1px))]:bg-bg"
      }`}
    >
      <div className="mx-auto w-full max-w-[1200px] md:px-8">
        <nav aria-label="Main" className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-6">
            <Wordmark />
            <div className="hidden items-center md:flex">{LINKS.map(link)}</div>
          </div>
          <div className="flex items-center gap-1">
            <HealthDot />
            <span className="hidden md:inline-flex">
              <ThemeToggle />
            </span>
            <AuthMenu />
            <span className="ml-1 hidden md:inline-flex">{cta}</span>
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center text-text md:hidden"
              aria-label={open ? t("nav.close") : t("nav.menu")}
              aria-expanded={open}
              onClick={() => setOpenFor(open ? null : path)}
            >
              {open ? <X size={22} /> : <List size={22} />}
            </button>
          </div>
        </nav>
      </div>
      {open && (
        <div className="mx-auto max-w-[1200px] border-t border-rule py-2 md:hidden">
          {LINKS.map(link)}
          <div className="flex items-center justify-between border-t border-rule pt-2">
            <ThemeToggle />
            {cta}
          </div>
        </div>
      )}
    </header>
  );
}
