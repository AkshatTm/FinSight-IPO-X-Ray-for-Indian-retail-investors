"use client";

import { Moon, Sun } from "@phosphor-icons/react";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";

export function LangToggle() {
  const { t, lang } = useT();
  const setLang = useUi((s) => s.setLang);
  const opt = (value: "en" | "hi", label: string, htmlLang: string) => (
    <button
      type="button"
      lang={htmlLang}
      aria-pressed={lang === value}
      onClick={() => setLang(value)}
      className={`h-11 min-w-11 px-2.5 text-sm ${
        lang === value ? "font-semibold text-text" : "text-muted hover:text-text"
      }`}
    >
      {label}
    </button>
  );
  return (
    <div role="group" aria-label={t("nav.language")} title={t("lang.tooltip")} className="flex items-center">
      {opt("en", "EN", "en")}
      <span aria-hidden className="h-4 w-px bg-rule" />
      {opt("hi", "हिंदी", "hi")}
    </div>
  );
}

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
