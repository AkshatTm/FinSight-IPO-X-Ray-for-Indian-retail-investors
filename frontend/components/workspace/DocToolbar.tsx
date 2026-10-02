"use client";

import { CaretLeft, CaretRight } from "@phosphor-icons/react";
import { useState } from "react";
import type { Schemas } from "@/lib/api/client";
import { STRINGS, type StringKey } from "@/lib/i18n";
import { useT } from "@/lib/useT";
import type { Zoom } from "./PageViewer";

type Doc = "rhp" | "prospectus";

export function DocSwitch({ doc, onChange, hasProspectus }: { doc: Doc; onChange: (d: Doc) => void; hasProspectus: boolean }) {
  const { t } = useT();
  const opt = (value: Doc, label: StringKey, tip: StringKey, disabled = false) => (
    <button
      key={value}
      type="button"
      role="radio"
      aria-checked={doc === value}
      disabled={disabled}
      title={t(tip)}
      onClick={() => onChange(value)}
      className={`h-11 px-3 text-sm disabled:opacity-40 ${
        doc === value ? "bg-stamp/10 font-semibold text-text" : "text-muted hover:text-text"
      }`}
    >
      {t(label)}
    </button>
  );
  return (
    <div role="radiogroup" className="flex overflow-hidden rounded-[6px] border border-rule bg-surface">
      {opt("rhp", "doc.rhp", "doc.rhpTip")}
      {opt("prospectus", "doc.prospectus", "doc.prospectusTip", !hasProspectus)}
    </div>
  );
}

function PageInput({ page, total, onGo }: { page: number; total: number; onGo: (n: number) => void }) {
  const { t } = useT();
  const [draft, setDraft] = useState<string | null>(null);
  const commit = () => {
    const n = Math.round(Number(draft));
    if (draft !== null && Number.isFinite(n)) onGo(Math.min(total, Math.max(1, n)));
    setDraft(null);
  };
  return (
    <label className="flex items-center gap-2 text-sm text-muted">
      <span className="sr-only-keep">{t("doc.pageLabel")}</span>
      <span aria-hidden>{t("doc.pageWord")}</span>
      <input
        type="number"
        inputMode="numeric"
        min={1}
        max={total}
        value={draft ?? String(page)}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setDraft(null);
          e.stopPropagation();
        }}
        className="h-11 w-20 rounded-[6px] border border-rule bg-surface px-2 text-center text-text"
      />
      <span aria-hidden>{t("doc.ofTotal", { total })}</span>
    </label>
  );
}

interface Props {
  doc: Doc;
  onDoc: (d: Doc) => void;
  hasProspectus: boolean;
  page: number;
  total: number;
  onPage: (n: number) => void;
  zoom: Zoom;
  onZoom: (z: Zoom) => void;
  sections: Schemas["SectionInfo"][];
  thumbs: boolean;
  onThumbs: () => void;
}

export function DocToolbar(p: Props) {
  const { t } = useT();
  const sections = p.sections.filter((s) => s.doc === p.doc);
  const sectionName = (s: Schemas["SectionInfo"]) => {
    const key = `doc.section.${s.id}` as StringKey;
    return key in STRINGS ? t(key) : s.title;
  };
  const btn = "inline-flex h-11 w-11 items-center justify-center rounded-[6px] border border-rule bg-surface hover:border-stamp disabled:opacity-40";
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-surface px-3 py-2">
      <DocSwitch doc={p.doc} onChange={p.onDoc} hasProspectus={p.hasProspectus} />
      <div className="flex items-center gap-1">
        <button type="button" className={btn} aria-label={t("doc.prev")} disabled={p.page <= 1} onClick={() => p.onPage(p.page - 1)}>
          <CaretLeft size={18} />
        </button>
        <PageInput page={p.page} total={p.total} onGo={p.onPage} />
        <button type="button" className={btn} aria-label={t("doc.next")} disabled={p.page >= p.total} onClick={() => p.onPage(p.page + 1)}>
          <CaretRight size={18} />
        </button>
      </div>
      <div role="radiogroup" aria-label="Zoom" className="hidden overflow-hidden md:flex rounded-[6px] border border-rule">
        {(["fit", "100", "150"] as const).map((z) => (
          <button
            key={z}
            type="button"
            role="radio"
            aria-checked={p.zoom === z}
            onClick={() => p.onZoom(z)}
            className={`h-11 px-3 text-sm ${p.zoom === z ? "bg-stamp/10 font-semibold" : "text-muted hover:text-text"}`}
          >
            {t(z === "fit" ? "doc.zoomFit" : z === "100" ? "doc.zoom100" : "doc.zoom150")}
          </button>
        ))}
      </div>
      {sections.length > 0 && (
        <label className="min-w-0 max-w-full text-sm">
          <span className="sr-only-keep">{t("doc.jump")}</span>
          <select
            value=""
            onChange={(e) => e.target.value && p.onPage(Number(e.target.value))}
            className="h-11 w-full max-w-full truncate rounded-[6px] border border-rule bg-surface px-2 text-muted"
          >
            <option value="">{t("doc.jump")}</option>
            {sections.map((s) => (
              <option key={s.id} value={s.start_page}>
                {sectionName(s)}
              </option>
            ))}
          </select>
        </label>
      )}
      <button
        type="button"
        aria-pressed={p.thumbs}
        onClick={p.onThumbs}
        className={`hidden h-11 rounded-[6px] border px-3 text-sm md:inline-flex md:items-center ${p.thumbs ? "border-stamp bg-stamp/10" : "border-rule text-muted hover:text-text"}`}
      >
        {t("doc.thumbs")}
      </button>
    </div>
  );
}
