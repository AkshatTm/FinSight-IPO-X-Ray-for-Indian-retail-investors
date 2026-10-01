"use client";

import { FIELD_CONTENT, pick } from "@/lib/content/fields";
import { formatMoney } from "@/lib/format";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { parseObjectsTable, resolveField, type XField } from "@/lib/xray";

/** Objects of the offer as horizontal bars, longest first; `[●]` rows last with a dashed bar (7.3.5). */
export function ObjectsBars({ ipoId, field }: { ipoId: string; field: XField }) {
  const { t, lang } = useT();
  const unit = useUi((s) => s.unit);
  const setHighlight = useUi((s) => s.setHighlight);
  const r = resolveField(field);
  const content = FIELD_CONTENT.objects_of_offer;

  if (r.notInDocument || r.value?.kind !== "table") {
    return <p className="text-sm text-muted">{pick(content.notInDocument!, lang)}</p>;
  }
  const rows = parseObjectsTable(r.value);
  const known = rows.filter((x) => x.inr !== null).sort((a, b) => Number(b.inr) - Number(a.inr));
  const unknown = rows.filter((x) => x.inr === null);
  const max = Math.max(1, ...known.map((x) => Number(x.inr)));

  const go = () =>
    setHighlight({ ipoId, doc: r.doc, page: r.page, bbox: r.doc === field.doc ? field.bbox : null, kind: "source" });

  return (
    <ul className="space-y-1">
      {[...known, ...unknown].map((row) => (
        <li key={row.label}>
          <button
            type="button"
            onClick={go}
            className="block min-h-11 w-full rounded-[6px] px-2 py-1.5 text-left hover:bg-surface-2"
          >
            <span className="flex items-baseline justify-between gap-3 text-sm">
              <span>{row.label}</span>
              <span className="shrink-0 font-medium">
                {row.inr !== null ? formatMoney(row.inr, unit, lang) : t("objects.notSet")}
              </span>
            </span>
            <span className="mt-1 block h-1.5 w-full rounded-full bg-surface-2">
              {row.inr !== null ? (
                <span className="block h-full rounded-full bg-stamp" style={{ width: `${(Number(row.inr) / max) * 100}%` }} />
              ) : (
                <span className="block h-full w-1/3 rounded-full border border-dashed border-muted" />
              )}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
