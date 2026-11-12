"use client";

import { Moon, Sun } from "@phosphor-icons/react";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";

export function ThemeToggle() {
  const { t } = useT();
  const theme = useUi((s) => s.theme);
  const setTheme = useUi((s) => s.setTheme);
  const Icon = theme === "dark" ? Sun : Moon;
  return (
    <button
      type="button"
      aria-label={t("nav.theme")}
      title={t("nav.theme")}
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="inline-flex h-11 w-11 items-center justify-center rounded-full text-muted hover:text-text"
    >
      <Icon size={20} weight="regular" />
    </button>
  );
}
