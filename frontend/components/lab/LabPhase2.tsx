"use client";

import { classifierLadder, financialChecks, novelty, pct, segmentation } from "@/lib/labB";
import { useT } from "@/lib/useT";
import { LabFrame, LabTable, Note, Stat } from "./LabFrame";

const f2 = (x: number) => x.toFixed(2);

/** B05 §7.1 (E13). */
export function LabSegmentation({ data }: { data: unknown }) {
  const { t } = useT();
  const s = segmentation(data);
  if (!s) return null;
  return (
    <LabFrame id="b-seg" heading={t("labb.seg.h")} shows={t("labb.seg.shows")}>
      <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-3">
        <Stat value={`${pct(s.f1)}%`} label={t("labb.seg.f1")} sub={t("labb.seg.pr", { p: pct(s.precision), r: pct(s.recall) })} />
        {s.nDocs > 0 && <Stat value={String(s.nDocs)} label={t("labb.seg.docs")} />}
        {s.corpusF1 !== null && <Stat value={`${pct(s.corpusF1)}%`} label={t("labb.seg.corpus")} />}
      </dl>
    </LabFrame>
  );
}

/** B05 §7.2 (E14, E15). */
export function LabChecks({ summary, redflags }: { summary: unknown; redflags: unknown }) {
  const { t } = useT();
  const c = financialChecks(summary, redflags);
  if (!c) return null;
  return (
    <LabFrame id="b-checks" heading={t("labb.chk.h")} shows={t("labb.chk.shows")}>
      <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-2">
        {c.nvm !== null && <Stat value={`${pct(c.nvm)}%`} label={t("labb.chk.nvm", { n: c.nValues })} />}
        {c.accuracy !== null && <Stat value={`${pct(c.accuracy)}%`} label={t("labb.chk.acc", { n: c.nFlags })} />}
      </dl>
      {c.labels.length > 0 && (
        <div className="mt-8">
          <LabTable
            head={[`${t("labb.chk.col.gold")} \\ ${t("labb.chk.col.pred")}`, ...c.labels]}
            rows={c.labels.map((l, i) => ({ key: l, cells: [l, ...c.confusion[i].map(String)] }))}
          />
        </div>
      )}
    </LabFrame>
  );
}

/** B05 §7.3 (E16): TF-IDF → base → large → teacher, macro-F1 with n. */
export function LabClassifier({ data }: { data: unknown }) {
  const { t } = useT();
  const rows = classifierLadder(data);
  if (!rows.length) return null;
  return (
    <LabFrame id="b-clf" heading={t("labb.clf.h")} shows={t("labb.clf.shows")}>
      <LabTable
        head={[t("labb.clf.col.model"), t("labb.clf.col.f1"), t("labb.clf.col.n")]}
        rows={rows.map((r) => ({
          key: r.key,
          cells: [
            r.label,
            r.std !== null && r.seeds ? `${f2(r.f1)} ${t("labb.clf.seeds", { std: f2(r.std), k: r.seeds })}` : f2(r.f1),
            String(r.n),
          ],
        }))}
      />
      <Note>{t("labb.clf.note")}</Note>
    </LabFrame>
  );
}

/** B05 §7.5 (E22): precision of "similar risk" at each τ, the chosen one marked. */
export function LabNovelty({ data }: { data: unknown }) {
  const { t } = useT();
  const v = novelty(data);
  if (!v) return null;
  return (
    <LabFrame id="b-novelty" heading={t("labb.nov.h")} shows={t("labb.nov.shows")}>
      <LabTable
        head={[t("labb.nov.col.tau"), t("labb.nov.col.p"), t("labb.nov.col.n")]}
        rows={v.points.map((p) => ({
          key: String(p.tau),
          cells: [p.tau === v.chosen ? `${f2(p.tau)} (${t("labb.nov.chosen")})` : f2(p.tau), `${pct(p.precision)}%`, String(p.n)],
        }))}
      />
    </LabFrame>
  );
}
