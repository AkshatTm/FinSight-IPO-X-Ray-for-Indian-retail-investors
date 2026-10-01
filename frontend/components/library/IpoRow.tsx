"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { apiGet, type Schemas } from "@/lib/api/client";
import { formatMoney, formatMonthYear, formatRupee } from "@/lib/format";
import type { Ipo } from "@/lib/library";
import { useXray } from "@/lib/api/hooks";
import { fieldById, resolveField } from "@/lib/xray";
import { useT } from "@/lib/useT";
import { FreshOfsBar } from "./FreshOfsBar";

function Preview({ id }: { id: string }) {
  const { t } = useT();
  const { data } = useXray(id);
  if (!data) return null;
  const price = fieldById(data.fields, "offer_price");
  const face = fieldById(data.fields, "face_value");
  const managers = fieldById(data.fields, "book_running_lead_managers");
  const money = (f: typeof price) => {
    const r = f && resolveField(f);
    return r?.value?.kind === "money" && r.value.value_inr ? formatRupee(r.value.value_inr) : t("lib.notSet");
  };
  const count = managers?.value?.kind === "list" ? managers.value.items.length : null;
  return (
    <dl className="grid grid-cols-3 gap-4 text-sm">
      <div>
        <dt className="text-xs text-muted">{t("lib.offerPrice")}</dt>
        <dd className="font-medium">{money(price)}</dd>
      </div>
      <div>
        <dt className="text-xs text-muted">{t("lib.faceValue")}</dt>
        <dd className="font-medium">{money(face)}</dd>
      </div>
      <div>
        <dt className="text-xs text-muted">{t("lib.managers")}</dt>
        <dd className="font-medium">{count ?? "—"}</dd>
      </div>
    </dl>
  );
}

export function IpoRow({ ipo }: { ipo: Ipo }) {
  const { t, lang } = useT();
  const qc = useQueryClient();
  const [peek, setPeek] = useState(false);

  const warm = () => {
    setPeek(true);
    void qc.prefetchQuery({
      queryKey: ["xray", ipo.id],
      queryFn: () => apiGet<Schemas["XRayResponse"]>(`/api/ipos/${ipo.id}/xray`),
    });
  };

  return (
    <li
      className="relative border-b border-rule last:border-b-0"
      onMouseEnter={warm}
      onMouseLeave={() => setPeek(false)}
      onFocusCapture={warm}
      onBlurCapture={() => setPeek(false)}
    >
      <Link
        href={`/ipos/${ipo.id}`}
        className="grid gap-x-8 gap-y-3 rounded-[6px] px-2 py-5 hover:bg-surface-2 md:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,1.5fr)_5.5rem] md:items-center"
      >
        <div className="min-w-0">
          <h2 className="truncate text-xl font-semibold tracking-tight">{ipo.company}</h2>
          {ipo.sector && <p className="text-sm text-muted">{ipo.sector}</p>}
        </div>
        <p className="text-sm text-muted">
          {ipo.listing_date ? t("lib.listed", { month: formatMonthYear(ipo.listing_date, lang) }) : ""}
        </p>
        <div>
          <p className="text-xs text-muted">{t("lib.issueSize")}</p>
          <p className="font-medium">
            {ipo.issue_size_inr ? formatMoney(ipo.issue_size_inr, "crore", lang) : t("lib.notSet")}
          </p>
        </div>
        <FreshOfsBar ipo={ipo} />
        <p className="text-sm text-muted md:text-right">{t("lib.pages", { n: ipo.rhp_pages })}</p>
      </Link>
      {peek && (
        <div
          aria-hidden
          className="pointer-events-none absolute left-2 right-2 top-full z-10 hidden -translate-y-1 rounded-[10px] border border-rule bg-surface px-4 py-3 shadow-[var(--shadow-float)] md:block"
        >
          <Preview id={ipo.id} />
        </div>
      )}
    </li>
  );
}
