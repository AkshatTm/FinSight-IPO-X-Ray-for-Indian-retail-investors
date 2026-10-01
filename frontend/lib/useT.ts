"use client";

import { useCallback } from "react";
import { t as translate, type StringKey } from "@/lib/i18n";
import { useUi } from "@/lib/store";

/** `const { t, lang } = useT()`; strings come from lib/i18n.ts only. */
export function useT() {
  const lang = useUi((s) => s.lang);
  const t = useCallback(
    (key: StringKey, vars?: Record<string, string | number>) => translate(key, lang, vars),
    [lang],
  );
  return { t, lang };
}
