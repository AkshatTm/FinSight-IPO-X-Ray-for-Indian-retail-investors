"use client";

import { useEffect } from "react";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { Drawer } from "./Drawer";

const ROWS = [
  ["/", "keys.focusInput"],
  ["Esc", "keys.closePanel"],
  ["← →", "keys.pages"],
  ["+ −", "keys.zoom"],
  ["?", "keys.help"],
] as const;

/** `?` opens the list of keys (spec 17). Ignored while typing in a field. */
export function ShortcutsDialog() {
  const { t } = useT();
  const open = useUi((s) => s.shortcuts);
  const setOpen = useUi((s) => s.setShortcuts);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (e.key !== "?" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable) return;
      e.preventDefault();
      setOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setOpen]);

  if (!open) return null;
  return (
    <Drawer title={t("keys.title")} onClose={() => setOpen(false)}>
      <ul className="mt-4">
        {ROWS.map(([k, label]) => (
          <li key={k} className="flex items-center justify-between gap-4 border-b border-rule py-3">
            <span>{t(label)}</span>
            <kbd className="rounded-[6px] border border-rule bg-surface-2 px-2 py-0.5 font-mono text-sm">{k}</kbd>
          </li>
        ))}
      </ul>
    </Drawer>
  );
}
