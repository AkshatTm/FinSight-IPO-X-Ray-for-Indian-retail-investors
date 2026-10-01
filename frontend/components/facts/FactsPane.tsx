"use client";

import { useState } from "react";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { GROUPS } from "@/lib/content/fields";
import { useXray } from "@/lib/api/hooks";
import { useT } from "@/lib/useT";
import { fieldById } from "@/lib/xray";
import { FactRow } from "./FactRow";
import { MoneySplit } from "./MoneySplit";
import { ObjectsBars } from "./ObjectsBars";

function Skeleton() {
  const { t } = useT();
  return (
    <div aria-busy="true" aria-label={t("facts.loadingRows")} className="space-y-4">
      {Array.from({ length: 7 }, (_, i) => (
        <div key={i} className="space-y-2">
          <div className="skeleton h-4 w-2/5" />
          <div className="skeleton h-5 w-4/5" />
        </div>
      ))}
    </div>
  );
}

function GroupTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-1 mt-6 text-sm font-semibold first:mt-0">{children}</h3>;
}

export function FactsPane({ ipoId }: { ipoId: string }) {
  const { t } = useT();
  const { data, error, isPending, refetch } = useXray(ipoId);
  const [compare, setCompare] = useState(false);

  return (
    <section data-pane="facts" aria-label={t("facts.title")} className="flex min-h-full flex-col p-4">
      <h2 className="text-lg font-semibold">{t("facts.title")}</h2>
      <p className="mb-4 text-sm text-muted">{t("facts.sub")}</p>

      {error ? (
        <ErrorBlock error={error} onRetry={() => void refetch()} />
      ) : isPending ? (
        <Skeleton />
      ) : (
        <div className="flex-1">
          <GroupTitle>{t("facts.group.offer")}</GroupTitle>
          <ul>
            {GROUPS[0].fields.map((id) => {
              const f = fieldById(data.fields, id);
              return f ? <FactRow key={id} ipoId={ipoId} field={f} compare={compare} /> : null;
            })}
          </ul>

          <GroupTitle>{t("facts.group.split")}</GroupTitle>
          <MoneySplit derived={data.derived} fresh={fieldById(data.fields, "fresh_issue_size")} />

          <GroupTitle>{t("facts.group.people")}</GroupTitle>
          <ul>
            {GROUPS[1].fields.map((id) => {
              const f = fieldById(data.fields, id);
              return f ? <FactRow key={id} ipoId={ipoId} field={f} compare={compare} /> : null;
            })}
          </ul>

          <GroupTitle>{t("facts.group.use")}</GroupTitle>
          {(() => {
            const f = fieldById(data.fields, "objects_of_offer");
            return f ? <ObjectsBars ipoId={ipoId} field={f} /> : null;
          })()}
        </div>
      )}

      {data && (
        <div className="mt-6 border-t border-rule pt-3">
          <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm">
            <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} className="h-4 w-4 accent-[var(--stamp)]" />
            {t("compare.toggle")}
          </label>
          {compare && <p className="text-xs text-muted">{t("compare.foot")}</p>}
        </div>
      )}
    </section>
  );
}
