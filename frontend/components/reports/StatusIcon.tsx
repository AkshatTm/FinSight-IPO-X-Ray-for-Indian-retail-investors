import { CheckCircle, MinusCircle, Warning, WarningOctagon } from "@phosphor-icons/react";
import type { FlagStatus } from "@/lib/report";

/** Red-flag status mark in the stamp blue (never red/green: status words carry the meaning). */
export function StatusIcon({ status, size = 20 }: { status: FlagStatus; size?: number }) {
  const cls = "shrink-0 text-stamp";
  if (status === "concern") return <WarningOctagon size={size} weight="fill" aria-hidden className={cls} />;
  if (status === "watch") return <Warning size={size} weight="bold" aria-hidden className={cls} />;
  if (status === "ok") return <CheckCircle size={size} aria-hidden className={cls} />;
  return <MinusCircle size={size} aria-hidden className="shrink-0 text-muted" />;
}
