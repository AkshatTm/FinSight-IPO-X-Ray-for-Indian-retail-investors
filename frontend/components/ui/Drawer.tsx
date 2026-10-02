"use client";

import { X } from "@phosphor-icons/react";
import { useEffect, useRef, type ReactNode } from "react";
import { useT } from "@/lib/useT";

interface Props {
  title: string;
  /** Optional mark shown before the title (verdict drawer). */
  icon?: ReactNode;
  onClose: () => void;
  children: ReactNode;
  /** Tailwind width class from `sm:`; phones always get a full-screen sheet. */
  widthClass?: string;
}

/** Right-side drawer: Esc closes, focus moves in and returns to the opener (spec 2.5: 220 ms in). */
export function Drawer({ title, icon, onClose, children, widthClass = "sm:w-[440px]" }: Props) {
  const { t } = useT();
  const closeBtn = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const opener = document.activeElement;
    closeBtn.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, [onClose]);

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} aria-hidden />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`drawer-in fixed inset-y-0 right-0 z-50 flex w-full flex-col overflow-y-auto border-l border-rule bg-surface p-5 shadow-[var(--shadow-float)] ${widthClass}`}
      >
        <div className="flex items-start justify-between gap-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            {icon}
            {title}
          </h2>
          <button ref={closeBtn} type="button" onClick={onClose} aria-label={t("nav.close")} className="-mr-2 -mt-2 inline-flex h-11 w-11 items-center justify-center text-muted hover:text-text">
            <X size={20} />
          </button>
        </div>
        {children}
      </aside>
    </>
  );
}
