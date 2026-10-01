"use client";

import { useState, type KeyboardEvent } from "react";
import type { Schemas } from "@/lib/api/client";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { DocToolbar } from "./DocToolbar";
import { PageViewer, pageUrl, type Zoom } from "./PageViewer";

function Thumbnails({ ipoId, doc, page, total, onPage }: { ipoId: string; doc: "rhp" | "prospectus"; page: number; total: number; onPage: (n: number) => void }) {
  const first = Math.max(1, Math.min(page - 4, total - 9));
  const pages = Array.from({ length: Math.min(10, total) }, (_, i) => first + i);
  return (
    <div className="flex gap-2 overflow-x-auto border-t border-rule bg-surface p-2">
      {pages.map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onPage(n)}
          aria-current={n === page ? "page" : undefined}
          aria-label={String(n)}
          className={`relative h-24 w-[4.5rem] shrink-0 overflow-hidden rounded-[4px] border bg-white ${n === page ? "border-stamp" : "border-rule"}`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- API page renders */}
          <img src={pageUrl(ipoId, doc, n)} alt="" loading="lazy" className="h-full w-full object-cover object-top" />
          <span className="absolute bottom-0 right-0 bg-surface/90 px-1 text-xs">{n}</span>
        </button>
      ))}
    </div>
  );
}

interface Props {
  ipoId: string;
  detail: Schemas["IpoDetail"];
}

export function DocumentPane({ ipoId, detail }: Props) {
  const { t } = useT();
  const view = useUi((s) => s.view);
  const setView = useUi((s) => s.setView);
  const highlight = useUi((s) => s.highlight);
  const [zoom, setZoom] = useState<Zoom>("fit");
  const [thumbs, setThumbs] = useState(false);

  const cur = view && view.ipoId === ipoId ? view : { ipoId, doc: "rhp" as const, page: 1 };
  const hasProspectus = !!detail.prospectus_pages;
  const total = cur.doc === "prospectus" ? (detail.prospectus_pages ?? detail.rhp_pages) : detail.rhp_pages;
  const go = (n: number) => setView({ ipoId, doc: cur.doc, page: Math.min(total, Math.max(1, n)) });

  const onKey = (e: KeyboardEvent) => {
    const el = e.target as HTMLElement;
    if (["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) return;
    if (e.key === "ArrowLeft") go(cur.page - 1);
    else if (e.key === "ArrowRight") go(cur.page + 1);
    else if (e.key === "+" || e.key === "=") setZoom((z) => (z === "fit" ? "100" : "150"));
    else if (e.key === "-") setZoom((z) => (z === "150" ? "100" : "fit"));
    else return;
    e.preventDefault();
  };

  const docName = t(cur.doc === "rhp" ? "doc.rhpShort" : "doc.prospectusShort");
  return (
    <section
      aria-label={t("ws.tab.document")}
      tabIndex={-1}
      onKeyDown={onKey}
      className="flex h-full min-h-0 flex-col rounded-[10px] border border-rule bg-surface"
    >
      <DocToolbar
        doc={cur.doc}
        onDoc={(d) => setView({ ipoId, doc: d, page: 1 })}
        hasProspectus={hasProspectus}
        page={cur.page}
        total={total}
        onPage={go}
        zoom={zoom}
        onZoom={setZoom}
        sections={detail.sections}
        thumbs={thumbs}
        onThumbs={() => setThumbs((v) => !v)}
      />
      <PageViewer
        ipoId={ipoId}
        doc={cur.doc}
        page={cur.page}
        total={total}
        pageSize={detail.page_size}
        zoom={zoom}
        highlight={highlight}
        label={t("doc.pageImageAlt", { doc: docName, n: cur.page })}
      />
      {thumbs && <Thumbnails ipoId={ipoId} doc={cur.doc} page={cur.page} total={total} onPage={go} />}
    </section>
  );
}
