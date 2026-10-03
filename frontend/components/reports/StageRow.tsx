"use client";

import { CheckCircle, Circle, CircleNotch, WarningCircle } from "@phosphor-icons/react";
import { useState } from "react";
import type { RowState } from "@/lib/jobs";
import { useT } from "@/lib/useT";

const ICON = {
  waiting: <Circle size={20} aria-hidden className="text-muted" />,
  running: <CircleNotch size={20} aria-hidden className="animate-spin text-stamp motion-reduce:animate-none" />,
  done: <CheckCircle size={20} weight="fill" aria-hidden className="text-stamp" />,
  failed: <WarningCircle size={20} aria-hidden className="text-muted" />,
};

/** One row of the processing list (B05 §4): icon, label, state text and time. */
export function StageRow({
  label,
  state,
  doneText,
  ms,
  reason,
  badge,
}: {
  label: string;
  state: RowState;
  doneText: string | null;
  ms: number | null;
  reason: string | null;
  badge?: React.ReactNode;
}) {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  return (
    <li className="flex gap-3 py-3" data-state={state}>
      <span className="mt-0.5">{ICON[state]}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className={state === "waiting" ? "text-muted" : "font-medium"}>{label}</span>
          {ms != null && state === "done" && <span className="text-xs tabular-nums text-muted">{(ms / 1000).toFixed(1)} s</span>}
        </div>
        {state === "done" && doneText && (
          <p className="mt-0.5 flex items-center gap-2 text-sm text-muted">
            {badge}
            {doneText}
          </p>
        )}
        {state === "failed" && (
          <div className="mt-0.5 text-sm">
            <span>{t("proc.failed")}</span>{" "}
            {reason && (
              <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="text-stamp underline underline-offset-2">
                {t("proc.details")}
              </button>
            )}
            {open && reason && <p className="mt-1 text-muted">{reason}</p>}
          </div>
        )}
      </div>
    </li>
  );
}
