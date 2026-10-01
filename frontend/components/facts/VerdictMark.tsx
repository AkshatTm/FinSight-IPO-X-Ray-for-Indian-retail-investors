"use client";

import { useT } from "@/lib/useT";

export type MarkState = "verified" | "unverifiable" | "contradicted" | "placeholder";

const COLOR: Record<MarkState, string> = {
  verified: "var(--ok)",
  unverifiable: "var(--query)",
  contradicted: "var(--bad)",
  placeholder: "var(--text-muted)",
};

/** Auditor-style marks drawn as SVG (not emoji): tick, "?" in a circle, cross, dashed box. */
export function MarkIcon({ state, size = 18 }: { state: MarkState; size?: number }) {
  const c = COLOR[state];
  const common = { stroke: c, fill: "none", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-hidden focusable="false" className="shrink-0">
      {state === "verified" && <path d="M3 9.8 L7.2 14 L15.2 3.8" {...common} />}
      {state === "contradicted" && <path d="M4 4 L14 14 M14.2 3.6 L3.8 14.4" {...common} />}
      {state === "unverifiable" && (
        <>
          <circle cx="9" cy="9" r="7" {...common} strokeWidth={1.5} />
          <path d="M6.9 7.2 C6.9 5.2 11.1 5.2 11.1 7.4 C11.1 8.9 9 8.8 9 10.6" {...common} strokeWidth={1.5} />
          <circle cx="9" cy="13" r="0.6" fill={c} stroke={c} strokeWidth={1} />
        </>
      )}
      {state === "placeholder" && <rect x="3" y="4.5" width="12" height="9" rx="1.5" {...common} strokeWidth={1.5} strokeDasharray="2.5 2" />}
    </svg>
  );
}

/** Shape + word + colour. The word may be visually hidden in dense tables but stays for screen readers. */
export function VerdictMark({ state, showWord = true }: { state: MarkState; showWord?: boolean }) {
  const { t } = useT();
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs font-medium" style={{ color: COLOR[state] }}>
      <MarkIcon state={state} />
      <span className={showWord ? "" : "sr-only-keep"}>{t(`verdict.${state}`)}</span>
    </span>
  );
}
