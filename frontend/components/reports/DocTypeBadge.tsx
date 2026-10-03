"use client";

import { DOC_SHORT_KEY, type DocKind } from "@/lib/doc";
import { useT } from "@/lib/useT";

export function DocTypeBadge({ type }: { type: DocKind }) {
  const { t } = useT();
  return (
    <span className="inline-flex h-6 items-center rounded-[4px] border border-rule bg-surface-2 px-2 text-xs font-semibold">
      {t(DOC_SHORT_KEY[type])}
    </span>
  );
}
