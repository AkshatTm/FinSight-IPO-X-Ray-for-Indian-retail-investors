"use client";

import { useQuery } from "@tanstack/react-query";
import { MarkIcon } from "@/components/facts/VerdictMark";
import { apiGet, type Schemas } from "@/lib/api/client";
import { useXray } from "@/lib/api/hooks";
import { fieldById, resolveField, scalarText } from "@/lib/xray";
import { ATHER_RHP_DOC_ID } from "@/lib/showcase";
import { useT } from "@/lib/useT";

const IPO = "ather-energy-2025";
const CYCLE = 9; // seconds; the scan takes 6.5 of them

interface Callout {
  at: number; // share of the page height where the scan reveals it (0-1)
  side: "left" | "right";
  label: string;
  value: string;
  cite: string;
  mark?: "verified" | "unverifiable" | "contradicted";
}

function useCallouts(): Callout[] {
  const { t } = useT();
  const xray = useXray(IPO);
  const level = useQuery({
    queryKey: ["risk-level", ATHER_RHP_DOC_ID],
    queryFn: () => apiGet<Schemas["RiskLevel"]>(`/api/docs/${ATHER_RHP_DOC_ID}/risk-level`),
    retry: false,
  }).data;
  const flags = useQuery({
    queryKey: ["redflags", ATHER_RHP_DOC_ID],
    queryFn: () => apiGet<Schemas["RedFlags"]>(`/api/docs/${ATHER_RHP_DOC_ID}/redflags`),
    retry: false,
  }).data;

  const out: Callout[] = [];
  const total = xray.data ? fieldById(xray.data.fields, "total_issue_size") : undefined;
  if (total) {
    const r = resolveField(total);
    const text = r.value ? scalarText(total.field_id, r.value, "crore", t("facts.perShare")) : null;
    if (text) out.push({ at: 0.2, side: "right", label: t("land.x.issue"), value: text, cite: t("facts.chip", { doc: t("doc.rhpShort"), n: r.page }), mark: "verified" });
  }
  const price = xray.data ? fieldById(xray.data.fields, "face_value") : undefined;
  if (price) {
    const r = resolveField(price);
    const text = r.value ? scalarText(price.field_id, r.value, "crore", t("facts.perShare")) : null;
    if (text) out.push({ at: 0.42, side: "left", label: t("land.x.face"), value: text, cite: t("facts.chip", { doc: t("doc.rhpShort"), n: r.page }), mark: "verified" });
  }
  const flag = (flags?.flags ?? []).find((f) => f.status === "concern") ?? (flags?.flags ?? []).find((f) => f.status === "watch");
  if (flag && flag.sentence) {
    const page = flag.evidence?.[0]?.page;
    out.push({ at: 0.62, side: "right", label: flag.title, value: flag.sentence.length > 70 ? `${flag.sentence.slice(0, 68).trimEnd()}…` : flag.sentence, cite: page ? t("facts.chip", { doc: t("doc.rhpShort"), n: page }) : t("land.x.rule"), mark: "unverifiable" });
  }
  if (level) out.push({ at: 0.82, side: "left", label: t("land.x.level"), value: t(`rl.${level.level}`), cite: t("land.x.vsPast") });
  return out;
}

/** A saffron scan line sweeps a real RHP page; the facts it finds pop out with their page citations. */
export function XrayScan() {
  const { t } = useT();
  const callouts = useCallouts();
  return (
    <div className="xray relative mx-auto w-full max-w-[400px]" style={{ ["--cycle" as string]: `${CYCLE}s` }}>
      <div className="relative overflow-hidden rounded-[14px] bg-white shadow-[0_30px_80px_rgba(0,0,0,0.55)]" style={{ aspectRatio: "595.44 / 841.68" }}>
        {/* eslint-disable-next-line @next/next/no-img-element -- static page image from the pipeline */}
        <img src="/landing/ather-rhp-p3.webp" alt={t("land.lens.alt")} width={910} height={1286} className="h-full w-full object-cover" draggable={false} />
        <span aria-hidden className="xray-trail" />
        <span aria-hidden className="xray-line" />
      </div>
      {callouts.map((c, i) => (
        <div
          key={c.label}
          className={`xray-callout absolute z-10 w-[220px] rounded-[12px] bg-surface p-3 text-text shadow-[var(--shadow-float)] ${c.side === "right" ? "left-[62%] sm:left-[68%]" : "right-[62%] sm:right-[68%]"}`}
          style={{ top: `${c.at * 100}%`, ["--d" as string]: `${c.at * 6.5}s`, zIndex: 10 + i }}
        >
          <p className="text-sm text-muted">{c.label}</p>
          <p className="mt-0.5 flex items-center gap-1.5 text-base font-semibold leading-snug">
            {c.mark && <MarkIcon state={c.mark} size={16} />}
            <span className="num">{c.value}</span>
          </p>
          <p className="mt-1.5 inline-block rounded-[6px] bg-surface-2 px-1.5 py-0.5 text-sm text-muted">{c.cite}</p>
        </div>
      ))}
    </div>
  );
}
