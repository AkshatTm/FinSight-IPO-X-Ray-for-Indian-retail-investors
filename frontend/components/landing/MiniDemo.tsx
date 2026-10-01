"use client";

import Link from "next/link";
import { useState } from "react";
import { PageViewer } from "@/components/workspace/PageViewer";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { useIpo, useXray } from "@/lib/api/hooks";
import { FIELD_CONTENT, pick } from "@/lib/content/fields";
import { scalarText, fieldById, resolveField } from "@/lib/xray";
import type { Highlight } from "@/lib/store";
import { useT } from "@/lib/useT";
import { Section } from "./Sections";

const DEMO_IPO = "ather-energy-2025";
const ROWS = ["fresh_issue_size", "offer_price", "total_issue_size", "face_value"];

/** Compact, read-only copy of the workspace: four facts and one page (spec 5.6). Own highlight state. */
export function MiniDemo() {
  const { t, lang } = useT();
  const xray = useXray(DEMO_IPO);
  const ipo = useIpo(DEMO_IPO);
  const [h, setH] = useState<Highlight | null>(null);
  const [nonce, setNonce] = useState(0);
  const detail = ipo.data;

  const rows = ROWS.map((id) => (xray.data ? fieldById(xray.data.fields, id) : undefined)).filter((f) => !!f);
  const view = h ?? { ipoId: DEMO_IPO, doc: "rhp" as const, page: 3, kind: "source" as const, nonce: 0 };

  return (
    <Section id="demo" heading={t("land.demo.h")}>
      <p className="mt-4 max-w-2xl text-lg text-muted">{t("land.demo.b")}</p>
      {xray.error || ipo.error ? (
        <div className="mt-8">
          <ErrorBlock error={xray.error ?? ipo.error} onRetry={() => void (xray.refetch(), ipo.refetch())} />
        </div>
      ) : (
        <div className="mt-8 grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <ul className="self-start rounded-[10px] border border-rule bg-surface">
            {rows.length === 0
              ? ROWS.map((r) => <li key={r} className="skeleton m-3 h-12" aria-busy="true" />)
              : rows.map((f) => {
                  const r = resolveField(f);
                  const c = FIELD_CONTENT[f.field_id];
                  const label = c ? pick(c.label, lang) : lang === "hi" ? f.label_hi : f.label_en;
                  const value = r.value ? (scalarText(f.field_id, r.value, "crore", lang, t("facts.perShare")) ?? "") : "";
                  const active = h?.page === r.page && h?.doc === r.doc && h.ipoId === DEMO_IPO && h.bbox === (r.doc === f.doc ? f.bbox : null);
                  return (
                    <li key={f.field_id} className="border-b border-rule last:border-b-0">
                      <button
                        type="button"
                        aria-pressed={active}
                        onClick={() => {
                          setNonce(nonce + 1);
                          setH({ ipoId: DEMO_IPO, doc: r.doc, page: r.page, bbox: r.doc === f.doc ? f.bbox : null, kind: "source", nonce: nonce + 1 });
                        }}
                        className={`flex min-h-14 w-full items-center justify-between gap-3 px-4 py-2 text-left hover:bg-surface-2 ${active ? "bg-stamp/5" : ""}`}
                      >
                        <span className="text-sm text-muted">{label}</span>
                        <span className="font-medium">{value}</span>
                      </button>
                    </li>
                  );
                })}
          </ul>
          <div className="flex h-[26rem] min-h-0 flex-col overflow-hidden rounded-[10px] border border-rule bg-surface">
            {detail ? (
              <PageViewer
                ipoId={DEMO_IPO}
                doc={view.doc}
                page={view.page}
                total={detail.rhp_pages}
                pageSize={detail.page_size}
                zoom="fit"
                highlight={h}
                label={t("doc.pageImageAlt", { doc: t(view.doc === "rhp" ? "doc.rhpShort" : "doc.prospectusShort"), n: view.page })}
              />
            ) : (
              <div className="skeleton h-full w-full" aria-busy="true" />
            )}
          </div>
        </div>
      )}
      <p className="mt-6">
        <Link href={`/ipos/${DEMO_IPO}`} className="inline-flex h-11 items-center text-stamp underline underline-offset-4">
          {t("land.demo.open")}
        </Link>
      </p>
    </Section>
  );
}
