"use client";

import Link from "next/link";
import { useState } from "react";
import { Drawer } from "@/components/ui/Drawer";
import { anchorFor, LEVELS, topReasons, type RiskLevel } from "@/lib/report";
import { useT } from "@/lib/useT";

const LEVEL_COLOUR = { low: "bg-ok", medium: "bg-query", high: "bg-bad" } as const;

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
  const percentile = level.percentile;
  return (
    <section aria-labelledby="rl-title" className="rounded-[10px] border border-rule bg-surface p-5">
      {shown ? (
        <>
          <h2 id="rl-title" className="font-serif text-2xl font-semibold tracking-tight">
            {t("rl.title", { level: t(`rl.${level.level}`) })}
          </h2>
          <ol className="mt-4 grid grid-cols-3 gap-1.5" aria-label={t("rl.title", { level: t(`rl.${level.level}`) })}>
            {LEVELS.map((l, i) => (
              <li key={l} aria-current={i === active ? "step" : undefined}>
                <span className={`block h-1.5 rounded-full ${i === active ? LEVEL_COLOUR[l] : "bg-surface-2"}`} />
                <span className={`mt-1.5 block text-xs ${i === active ? "font-semibold text-text" : "text-muted"}`}>{t(`rl.${l}`)}</span>
              </li>
            ))}
          </ol>
          {percentile != null && n > 0 ? (
            <p className="mt-4 text-sm">{t("rl.line", { p: Math.round(percentile), n })}</p>
          ) : (
            n > 0 && <p className="mt-4 text-sm text-muted">{t("rl.noPercentile")}</p>
          )}
          {level.provisional && <p className="mt-2 text-xs text-muted">{t("rl.provisional")}</p>}
          {level.reasons.length > 0 && (
            <div className="mt-5 border-t border-rule pt-4">
              <h3 className="text-sm font-semibold">{t("rl.why")}</h3>
              <ul className="mt-2 space-y-1.5 text-sm">
                {topReasons(level).map((r) => (
                  <li key={`${r.source}-${r.id}`}>
                    <a
                      href={`#${anchorFor(r.source, r.id)}`}
                      className="underline decoration-rule underline-offset-4 hover:decoration-stamp"
                      onClick={(e) => {
                        e.preventDefault();
                        onReason(`#${anchorFor(r.source, r.id)}`);
                      }}
                    >
                      {r.source === "override" ? t("rl.override", { label: r.label }) : t("rl.reason", { label: r.label, points: r.points })}
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
          <button type="button" className="rounded-[6px] border border-rule px-4 py-2 text-sm font-medium hover:bg-surface-2" onClick={() => setShown(true)}>
            {t("rl.show")}
          </button>
        </>
      )}
      <p className="mt-5 text-xs leading-relaxed text-muted" data-testid="risk-disclaimer">{t("rl.disclaimer")}</p>
      <button type="button" className="mt-3 text-sm text-stamp underline underline-offset-4" onClick={() => setHow(true)}>
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
