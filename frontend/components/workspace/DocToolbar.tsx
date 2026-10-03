"use client";

import { CaretLeft, CaretRight, DotsThree } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import type { Schemas } from "@/lib/api/client";
import { STRINGS, type StringKey } from "@/lib/i18n";
import { useT } from "@/lib/useT";
import type { Zoom } from "./PageViewer";
import type { DocKind } from "@/lib/doc";

type Doc = DocKind;

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
      className={`h-11 px-2 text-sm disabled:opacity-40 md:px-3 ${
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

function ZoomGroup({ zoom, onZoom, className }: { zoom: Zoom; onZoom: (z: Zoom) => void; className: string }) {
  const { t } = useT();
  return (
    <div role="radiogroup" aria-label="Zoom" className={`overflow-hidden rounded-[6px] border border-rule ${className}`}>
      {(["fit", "100", "150"] as const).map((z) => (
        <button
          key={z}
          type="button"
          role="radio"
          aria-checked={zoom === z}
          onClick={() => onZoom(z)}
          className={`h-11 px-3 text-sm ${zoom === z ? "bg-stamp/10 font-semibold" : "text-muted hover:text-text"}`}
        >
          {t(z === "fit" ? "doc.zoomFit" : z === "100" ? "doc.zoom100" : "doc.zoom150")}
        </button>
      ))}
    </div>
  );
}

function SectionJump({ sections, onPage, className }: { sections: Schemas["SectionInfo"][]; onPage: (n: number) => void; className: string }) {
  const { t } = useT();
  const name = (s: Schemas["SectionInfo"]) => {
    const key = `doc.section.${s.id}` as StringKey;
    return key in STRINGS ? t(key) : s.title;
  };
  if (sections.length === 0) return null;
  return (
    <label className={`min-w-0 max-w-full text-sm ${className}`}>
      <span className="sr-only-keep">{t("doc.jump")}</span>
      <select
        value=""
        onChange={(e) => e.target.value && onPage(Number(e.target.value))}
        className="h-11 w-full max-w-full truncate rounded-[6px] border border-rule bg-surface px-2 text-muted"
      >
        <option value="">{t("doc.jump")}</option>
        {sections.map((s) => (
          <option key={s.id} value={s.start_page}>
            {name(s)}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Phone only: the controls that do not fit on one row (zoom, section jump, thumbnails). */
function MoreMenu(p: Props & { sections: Schemas["SectionInfo"][] }) {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  return (
    <div ref={root} className="relative md:hidden">
      <button
        type="button"
        aria-label={t("doc.more")}
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex h-11 w-11 items-center justify-center rounded-[6px] border bg-surface ${open ? "border-stamp" : "border-rule"}`}
      >
        <DotsThree size={22} weight="bold" />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-30 mt-1 flex w-[min(20rem,calc(100vw-1.5rem))] flex-col gap-2 rounded-[10px] border border-rule bg-surface p-3 shadow-[var(--shadow-float)]">
          <ZoomGroup zoom={p.zoom} onZoom={p.onZoom} className="flex" />
          <SectionJump
            sections={p.sections}
            onPage={(n) => {
              p.onPage(n);
              setOpen(false);
            }}
            className="block"
          />
          <button
            type="button"
            aria-pressed={p.thumbs}
            onClick={() => {
              p.onThumbs();
              setOpen(false);
            }}
            className={`h-11 rounded-[6px] border px-3 text-sm ${p.thumbs ? "border-stamp bg-stamp/10" : "border-rule text-muted"}`}
          >
            {t("doc.thumbs")}
          </button>
        </div>
      )}
    </div>
  );
}

export function DocToolbar(p: Props) {
  const { t } = useT();
  const sections = p.sections.filter((s) => s.doc === p.doc);
  const btn = "inline-flex h-11 w-11 items-center justify-center rounded-[6px] border border-rule bg-surface hover:border-stamp disabled:opacity-40";
  return (
    <div className="relative flex items-center gap-1 border-b border-rule bg-surface px-2 py-2 md:flex-wrap md:gap-2 md:px-3">
      <DocSwitch doc={p.doc} onChange={p.onDoc} hasProspectus={p.hasProspectus} />
      <div className="flex min-w-0 flex-1 items-center justify-center gap-1 md:flex-none md:justify-start">
        <button type="button" className={btn} aria-label={t("doc.prev")} disabled={p.page <= 1} onClick={() => p.onPage(p.page - 1)}>
          <CaretLeft size={18} />
        </button>
        <span className="whitespace-nowrap px-1 text-sm text-muted md:hidden" aria-live="polite">
          {t("doc.pageOf", { n: p.page, total: p.total })}
        </span>
        <div className="hidden md:block">
          <PageInput page={p.page} total={p.total} onGo={p.onPage} />
        </div>
        <button type="button" className={btn} aria-label={t("doc.next")} disabled={p.page >= p.total} onClick={() => p.onPage(p.page + 1)}>
          <CaretRight size={18} />
        </button>
      </div>
      <ZoomGroup zoom={p.zoom} onZoom={p.onZoom} className="hidden md:flex" />
      <SectionJump sections={sections} onPage={p.onPage} className="hidden md:block" />
      <button
        type="button"
        aria-pressed={p.thumbs}
        onClick={p.onThumbs}
        className={`hidden h-11 rounded-[6px] border px-3 text-sm md:inline-flex md:items-center ${p.thumbs ? "border-stamp bg-stamp/10" : "border-rule text-muted hover:text-text"}`}
      >
        {t("doc.thumbs")}
      </button>
      <MoreMenu {...p} sections={sections} />
    </div>
  );
}
