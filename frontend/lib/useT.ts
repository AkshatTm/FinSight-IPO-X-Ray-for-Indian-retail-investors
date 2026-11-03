"use client";

import { t, type StringKey } from "@/lib/copy";

/** `const { t } = useT()`; strings come from lib/copy.ts only. */
export function useT() {
  return { t: (key: StringKey, vars?: Record<string, string | number>) => t(key, vars) };
}
