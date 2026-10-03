"use client";

import { useEffect, useRef, useState } from "react";
import type { Highlight } from "@/lib/store";
import { useT } from "@/lib/useT";
import type { DocKind } from "@/lib/doc";

export type Zoom = "fit" | "100" | "150";

/** `width` asks the API for a smaller WebP (the thumbnail strip); omit it for the full page. */
export const pageUrl = (ipoId: string, doc: string, n: number, width?: number) =>
  `/api/ipos/${ipoId}/pages/${n}?doc=${doc}${width ? `&w=${width}` : ""}`;

const VERDICT_VAR: Record<Highlight["kind"], string> = {
  source: "--stamp",
  verified: "--ok",
  unverifiable: "--query",
  contradicted: "--bad",
};

/** Box over the page. Positions are percentages of the page, so zoom never moves it. */
export function HighlightBox({ h, pageW, pageH }: { h: Highlight; pageW: number; pageH: number }) {
  const [x0, y0, x1, y1] = h.bbox!;
  const color = `var(${VERDICT_VAR[h.kind]})`;
  return (
    <div
      key={h.nonce}
      data-testid="highlight"
      data-kind={h.kind}
      className="highlight-in pointer-events-none absolute"
      style={{
        left: `${(x0 / pageW) * 100}%`,
        top: `${(y0 / pageH) * 100}%`,
        width: `${((x1 - x0) / pageW) * 100}%`,
        height: `${((y1 - y0) / pageH) * 100}%`,
        outline: `1.5px solid ${color}`,
        background: `color-mix(in srgb, ${color} 18%, transparent)`,
        borderRadius: 2,
      }}
    />
  );
}

interface Props {
  ipoId: string;
  doc: DocKind;
  page: number;
  total: number;
  pageSize: { width: number; height: number };
  zoom: Zoom;
  highlight: Highlight | null;
  label: string;
}

export function PageViewer({ ipoId, doc, page, total, pageSize, zoom, highlight, label }: Props) {
  const { t } = useT();
  const { width: W, height: H } = pageSize;
  const [loaded, setLoaded] = useState<string | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const src = pageUrl(ipoId, doc, page);
  const ready = loaded === src;

  // Warm the next page so turning pages is instant.
  useEffect(() => {
    if (!ready || page >= total) return;
    const img = new Image();
    img.src = pageUrl(ipoId, doc, page + 1);
  }, [ready, ipoId, doc, page, total]);

  const showBox = !!highlight?.bbox && highlight.ipoId === ipoId && highlight.doc === doc && highlight.page === page;

  // Bring the box into view when the page is zoomed past the pane.
  useEffect(() => {
    if (!showBox || !ready) return;
    // Scroll only the page scroller; scrollIntoView would also move the whole window.
    const box = scroller.current?.querySelector<HTMLElement>("[data-testid=highlight]");
    const sc = scroller.current;
    if (!box || !sc) return;
    const b = box.getBoundingClientRect();
    const r = sc.getBoundingClientRect();
    sc.scrollTo({
      top: sc.scrollTop + (b.top - r.top) - (r.height - b.height) / 2,
      left: sc.scrollLeft + (b.left - r.left) - (r.width - b.width) / 2,
    });
  }, [showBox, ready, highlight?.nonce]);

  const widthStyle = zoom === "fit" ? { width: "100%" } : { width: `${W * (zoom === "100" ? 1 : 1.5)}px` };

  return (
    <div ref={scroller} className="min-h-0 flex-1 overflow-auto bg-surface-2 p-3" data-testid="page-scroller">
      <div
        className="relative mx-auto bg-white shadow-[0_1px_3px_rgba(24,32,46,0.15)]"
        style={{ ...widthStyle, aspectRatio: `${W} / ${H}`, maxWidth: zoom === "fit" ? `${W * 1.6}px` : undefined }}
      >
        {!ready && !failed && <div className="skeleton absolute inset-0 !rounded-none" aria-hidden />}
        {failed === src ? (
          <p className="absolute inset-0 grid place-items-center p-6 text-center text-sm text-muted">{t("err.page_out_of_range")}</p>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- pages come from the API as WebP; next/image would re-encode them
          <img
            key={src}
            src={src}
            alt={label}
            width={W}
            height={H}
            draggable={false}
            onLoad={() => setLoaded(src)}
            onError={() => setFailed(src)}
            className="absolute inset-0 h-full w-full select-none"
          />
        )}
        {showBox && ready && <HighlightBox h={highlight} pageW={W} pageH={H} />}
      </div>
    </div>
  );
}
