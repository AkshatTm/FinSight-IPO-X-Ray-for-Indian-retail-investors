"use client";

import { formatPercent } from "@/lib/format";
import { isPureOfs, splitPct, type Ipo } from "@/lib/library";
import { useT } from "@/lib/useT";

/** Slim two-part bar: stamp blue = fresh, grey = offer for sale (spec 6.3). */
export function FreshOfsBar({ ipo }: { ipo: Ipo }) {
  const { t } = useT();
  const split = splitPct(ipo);
  if (!split) return <span className="text-sm text-muted">{t("lib.notSet")}</span>;
  const pure = isPureOfs(ipo);
  const fresh = t("lib.fresh", { x: formatPercent(split.fresh) });
  const ofs = t("lib.ofsPct", { y: formatPercent(split.ofs) });
  const label = pure ? t("lib.onlyOfs") : `${fresh}, ${ofs}`;
  return (
    <div>
      <div
        role="img"
        aria-label={label}
        className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-2"
      >
        {!pure && <div className="bg-stamp" style={{ width: `${split.fresh}%` }} />}
        <div className="bg-rule" style={{ width: `${pure ? 100 : split.ofs}%` }} />
      </div>
      <p className="mt-1.5 flex justify-between gap-3 text-xs text-muted">
        {pure ? (
          <span>{label}</span>
        ) : (
          <>
            <span>{fresh}</span>
            <span>{ofs}</span>
          </>
        )}
      </p>
    </div>
  );
}
