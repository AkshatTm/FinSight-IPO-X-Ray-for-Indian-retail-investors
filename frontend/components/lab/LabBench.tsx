"use client";

import { useLabBench } from "@/lib/api/hooks";
import { useT } from "@/lib/useT";
import { LabFrame, LabTable, Note } from "./LabFrame";

interface Score {
  mean: number;
  low: number;
  high: number;
}
type Rec = Record<string, unknown>;

const isRec = (x: unknown): x is Rec => typeof x === "object" && x !== null;

/** `mean (low–high)` as percentages, or an en dash when the system has no such score. */
function score(x: unknown): string {
  if (!isRec(x) || typeof x.mean !== "number") return "–";
  const s = x as unknown as Score;
  const p = (v: number) => Math.round(v * 100);
  return `${p(s.mean)}% (${p(s.low)}–${p(s.high)})`;
}

/** FinSight Bench v1 (C4.1): one row per scored system; hides when no system was scored. */
export function LabBench() {
  const { t } = useT();
  const { data } = useLabBench();
  if (!data || !isRec(data.systems)) return null;
  const systems = Object.entries(data.systems).filter(([, v]) => isRec(v));
  if (!systems.length) return null;
  const ipos = Array.isArray(data.ipos) ? data.ipos.length : 0;
  const when = typeof data.frozen_utc === "string" ? data.frozen_utc.slice(0, 10) : "";
  const part = (v: unknown, task: string, key: string) => (isRec(v) && isRec(v[task]) ? (v[task] as Rec)[key] : undefined);
  return (
    <LabFrame id="c-bench" heading={t("labb.bench.h")} shows={t("labb.bench.shows")}>
      <LabTable
        head={[t("labb.bench.col.system"), t("labb.bench.col.a"), t("labb.bench.col.b"), t("labb.bench.col.c"), t("labb.bench.col.abstain")]}
        rows={systems.map(([name, v]) => ({
          key: name,
          cells: [
            name,
            score(part(v, "A", "nvm")),
            score(part(v, "B", "status_accuracy")),
            score(part(v, "C", "correct_answerable")),
            score(part(v, "C", "abstention_unanswerable")),
          ],
        }))}
      />
      <Note>{t("labb.bench.note", { n: ipos, v: String(data.bench ?? "v1"), when })}</Note>
    </LabFrame>
  );
}
