"use client";

import { formatPercent } from "@/lib/format";
import { useT } from "@/lib/useT";
import { resolveField, type XField } from "@/lib/xray";

interface Props {
  derived: Record<string, string>;
  fresh?: XField;
}

/** Fresh issue vs offer for sale, from the derived percentages (spec 7.3.4). */
export function MoneySplit({ derived, fresh }: Props) {
  const { t } = useT();
  const pureOfs = !!fresh && resolveField(fresh).notInDocument;
  const f = derived.fresh_share_pct != null ? Number(derived.fresh_share_pct) : null;
  const o = derived.ofs_share_pct != null ? Number(derived.ofs_share_pct) : null;

  if (!pureOfs && (f == null || o == null)) {
    return <p className="text-sm text-muted">{t("split.unknown")}</p>;
  }
  const fresh_ = pureOfs ? 0 : (f as number);
  const ofs_ = pureOfs ? 100 : (o as number);
  const summary = pureOfs
    ? t("split.pureOfs")
    : `${t("split.company")} ${formatPercent(fresh_)}, ${t("split.sellers")} ${formatPercent(ofs_)}`;
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium">{t("split.title")}</h3>
      <div role="img" aria-label={summary} className="flex h-3 w-full overflow-hidden rounded-full bg-surface-2">
        {fresh_ > 0 && <div className="bg-stamp" style={{ width: `${fresh_}%` }} />}
        <div className="bg-rule" style={{ width: `${ofs_}%` }} />
      </div>
      {pureOfs ? (
        <p className="mt-2 text-sm">{t("split.pureOfs")}</p>
      ) : (
        <>
          <dl className="mt-2 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="flex items-center gap-1.5 text-muted">
                <span aria-hidden className="h-2 w-2 rounded-full bg-stamp" />
                {t("split.company")}
              </dt>
              <dd className="font-medium">{formatPercent(fresh_)}</dd>
            </div>
            <div>
              <dt className="flex items-center gap-1.5 text-muted">
                <span aria-hidden className="h-2 w-2 rounded-full bg-rule" />
                {t("split.sellers")}
              </dt>
              <dd className="font-medium">{formatPercent(ofs_)}</dd>
            </div>
          </dl>
          <p className="mt-2 text-sm text-muted">{t("split.helper")}</p>
        </>
      )}
    </div>
  );
}
