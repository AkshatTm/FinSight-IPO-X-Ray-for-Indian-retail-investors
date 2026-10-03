"use client";

import Link from "next/link";
import { useState } from "react";
import { Drawer } from "@/components/ui/Drawer";
import { anchorFor, LEVELS, topReasons, type RiskLevel } from "@/lib/report";
import { useT } from "@/lib/useT";

/**
 * Risk level card (B05 §5.3). The disclaimer is always shown and has no close control; with
 * `behind_click` the level waits for "Show the risk level", the disclaimer stays visible.
 */
export function RiskLevelCard({ level, onReason }: { level: RiskLevel; onReason: (hash: string) => void }) {
  const { t } = useT();
  const [shown, setShown] = useState(!level.behind_click);
  const [how, setHow] = useState(false);
  const active = LEVELS.indexOf(level.level);
  const n = level.corpus_n;
  return (
    <section aria-labelledby="rl-title" className="rounded-[10px] border border-rule bg-surface p-5">
      {shown ? (
        <>
          <h2 id="rl-title" className="text-xl font-semibold">{t("rl.title", { level: t(`rl.${level.level}`) })}</h2>
          <ol className="mt-3 grid grid-cols-3 gap-1" aria-label={t("rl.title", { level: t(`rl.${level.level}`) })}>
            {LEVELS.map((l, i) => (
              <li key={l} aria-current={i === active ? "step" : undefined} className={`rounded-full px-2 py-1 text-center text-xs ${i === active ? "bg-stamp font-semibold text-bg" : "bg-surface-2 text-muted"}`}>
                {t(`rl.${l}`)}
              </li>
            ))}
          </ol>
          {n > 0 && <p className="mt-3 text-sm">{t("rl.line", { p: Math.round(level.percentile), n })}</p>}
          {level.provisional && <p className="mt-2 text-xs text-muted">{t("rl.provisional")}</p>}
          {level.reasons.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold">{t("rl.why")}</h3>
              <ul className="mt-1 space-y-1 text-sm">
                {topReasons(level).map((r) => (
                  <li key={`${r.source}-${r.id}`}>
                    <a
                      href={`#${anchorFor(r.source, r.id)}`}
                      className="underline decoration-dotted underline-offset-2 hover:text-stamp"
                      onClick={(e) => {
                        e.preventDefault();
                        onReason(`#${anchorFor(r.source, r.id)}`);
                      }}
                    >
                      {t("rl.reason", { label: r.label, points: r.points })}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      ) : (
        <>
          <h2 id="rl-title" className="sr-only">{t("rl.show")}</h2>
          <button type="button" className="rounded-full border border-rule px-4 py-2 text-sm font-medium hover:bg-surface-2" onClick={() => setShown(true)}>
            {t("rl.show")}
          </button>
        </>
      )}
      <p className="mt-4 rounded-[8px] bg-surface-2 p-3 text-xs" data-testid="risk-disclaimer">{t("rl.disclaimer")}</p>
      <button type="button" className="mt-3 text-sm underline underline-offset-2" onClick={() => setHow(true)}>
        {t("rl.how")}
      </button>
      {how && (
        <Drawer title={t("rl.how")} onClose={() => setHow(false)}>
          <div className="space-y-3 text-sm">
            <p>{t("rlm.intro")}</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>{t("rlm.points1")}</li>
              <li>{t("rlm.points2")}</li>
            </ul>
            <p>{t("rlm.share")}</p>
            <p>{t("rlm.compare", { n })}</p>
            <p>{t("rlm.notAdvice")}</p>
            <Link href="/lab" className="underline underline-offset-2">{t("rlm.outcomes")}</Link>
          </div>
        </Drawer>
      )}
    </section>
  );
}
