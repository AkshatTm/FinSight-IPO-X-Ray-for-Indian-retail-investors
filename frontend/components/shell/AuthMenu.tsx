"use client";

import { UserCircle } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth/supabase";
import { useT } from "@/lib/useT";

/** Sign in, or the account menu (My uploads, Sign out) — B05 §1. Hidden when auth is off locally. */
export function AuthMenu() {
  const { t } = useT();
  const { mode, ready, user, signIn, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    window.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", esc);
    };
  }, [open]);

  if (mode === "off" || !ready) return null;
  if (!user) {
    return (
      <button type="button" onClick={() => void signIn()} className="flex h-11 items-center px-3 text-sm text-muted hover:text-text">
        {t("nav.signIn")}
      </button>
    );
  }
  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-label={t("nav.account")}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex h-11 w-11 items-center justify-center"
      >
        <UserCircle size={24} aria-hidden />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-12 z-50 w-48 rounded-[10px] border border-rule bg-surface p-1 shadow-[var(--shadow-float)]">
          <Link role="menuitem" href="/me/uploads" onClick={() => setOpen(false)} className="flex h-10 items-center rounded-[6px] px-3 text-sm hover:bg-surface-2">
            {t("nav.myUploads")}
          </Link>
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              void signOut();
            }}
            className="flex h-10 w-full items-center rounded-[6px] px-3 text-left text-sm hover:bg-surface-2"
          >
            {t("nav.signOut")}
          </button>
        </div>
      )}
    </div>
  );
}
