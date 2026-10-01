"use client";

import { X } from "@phosphor-icons/react";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { useHealth } from "./HealthDot";

export function ColdStartBanner() {
  const { t } = useT();
  const { state } = useHealth();
  const dismissed = useUi((s) => s.coldBannerDismissed);
  const dismiss = useUi((s) => s.dismissColdBanner);
  if (state !== "warming" || dismissed) return null;
  return (
    <div role="status" className="border-b border-rule bg-surface-2">
      <div className="mx-auto flex max-w-[1120px] items-start justify-between gap-3 px-4 py-2 text-sm md:px-6">
        <p>
          <strong className="font-semibold">{t("banner.coldBold")}</strong> {t("banner.coldRest")}
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label={t("banner.dismiss")}
          className="-my-1 inline-flex h-11 w-11 shrink-0 items-center justify-center text-muted hover:text-text"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
