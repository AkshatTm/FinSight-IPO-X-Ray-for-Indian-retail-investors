"use client";

import { useId, useState, type ReactNode } from "react";
import { glossaryText } from "@/lib/content/glossary";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";

/**
 * Finance term with a dotted underline. Hover, focus or tap opens a short definition and a link
 * into the glossary drawer (spec 4.5). Enter opens, Esc closes.
 */
export function GlossaryTerm({ id, children }: { id: string; children: ReactNode }) {
  const { t, lang } = useT();
  const openGlossary = useUi((s) => s.openGlossary);
  const [open, setOpen] = useState(false);
  const pop = useId();
  const g = glossaryText(id, lang);
  if (!g) return <>{children}</>;
  return (
    <span className="relative inline-block" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className="term inline"
        aria-expanded={open}
        aria-describedby={open ? pop : undefined}
        onClick={() => setOpen((v) => !v)}
        onFocus={() => setOpen(true)}
        onBlur={(e) => {
          if (!e.currentTarget.parentElement?.contains(e.relatedTarget)) setOpen(false);
        }}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
      >
        {children}
      </button>
      {open && (
        <span
          id={pop}
          role="tooltip"
          className="absolute left-0 top-full z-30 mt-1 block w-64 rounded-[10px] border border-rule bg-surface p-3 text-left text-sm font-normal text-text shadow-[var(--shadow-float)]"
        >
          <span className="block">{g.short}</span>
          <button
            type="button"
            className="mt-2 inline-flex h-11 items-center text-stamp underline underline-offset-2"
            onClick={() => {
              setOpen(false);
              openGlossary(id);
            }}
          >
            {t("glossary.more")}
          </button>
        </span>
      )}
    </span>
  );
}
