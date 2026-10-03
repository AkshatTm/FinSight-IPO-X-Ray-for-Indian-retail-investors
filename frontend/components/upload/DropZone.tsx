"use client";

import { FilePdf } from "@phosphor-icons/react";
import { useRef, useState, type DragEvent } from "react";
import { useT } from "@/lib/useT";

/** Drag-and-drop or click to pick one PDF (B05 §3). Disabled when signed out or paused. */
export function DropZone({ disabled, busy, maxMb, onFile }: { disabled: boolean; busy: boolean; maxMb: number; onFile: (f: File) => void }) {
  const { t } = useT();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const off = disabled || busy;

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f && !off) onFile(f);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!off) setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      aria-disabled={off}
      className={`flex flex-col items-center rounded-[12px] border-2 border-dashed px-6 py-12 text-center transition-colors ${
        over ? "border-stamp bg-surface-2" : "border-rule bg-surface"
      } ${off ? "opacity-60" : ""}`}
    >
      <FilePdf size={36} aria-hidden className="text-muted" />
      <p className="mt-3 text-base">
        {t("up.drop")}{" "}
        <button
          type="button"
          disabled={off}
          onClick={() => input.current?.click()}
          className="font-semibold text-stamp underline underline-offset-2 disabled:cursor-not-allowed"
        >
          {t("up.choose")}
        </button>
      </p>
      <p className="mt-1 text-sm text-muted">{t("up.helper", { max_mb: maxMb })}</p>
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        data-testid="upload-input"
        disabled={off}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
    </div>
  );
}
