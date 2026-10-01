"use client";

import { ApiError } from "@/lib/api/client";
import { errorMessage } from "@/lib/i18n";
import { useT } from "@/lib/useT";

/** Generic error block, shown inside the failing panel, never full page (spec 4.4). */
export function ErrorBlock({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t, lang } = useT();
  const code = error instanceof ApiError ? error.code : undefined;
  return (
    <div role="alert" className="rounded-[10px] border border-rule bg-surface p-5">
      <h2 className="text-lg font-semibold">{t("error.title")}</h2>
      <p className="mt-1 text-muted">{errorMessage(code, lang)}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 h-11 rounded-[6px] border border-rule bg-surface-2 px-4 text-sm font-medium hover:border-stamp"
        >
          {t("error.retry")}
        </button>
      )}
    </div>
  );
}
