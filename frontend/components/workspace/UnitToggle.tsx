"use client";

import { useUi } from "@/lib/store";
import type { Unit } from "@/lib/format";
import { useT } from "@/lib/useT";

const UNITS: Unit[] = ["crore", "million", "lakh", "full"];

/** Applies everywhere amounts are shown. No animation on switch: it is a frequent action. */
export function UnitToggle() {
  const { t } = useT();
  const unit = useUi((s) => s.unit);
  const setUnit = useUi((s) => s.setUnit);
  return (
    <div
      role="radiogroup"
      aria-label={t("unit.tooltip")}
      title={t("unit.tooltip")}
      className="flex overflow-hidden rounded-[6px] border border-rule bg-surface"
    >
      {UNITS.map((u) => (
        <button
          key={u}
          type="button"
          role="radio"
          aria-checked={unit === u}
          onClick={() => setUnit(u)}
          className={`h-11 px-3 text-sm ${unit === u ? "bg-stamp/10 font-semibold text-text" : "text-muted hover:text-text"}`}
        >
          {t(`unit.${u}`)}
        </button>
      ))}
    </div>
  );
}
