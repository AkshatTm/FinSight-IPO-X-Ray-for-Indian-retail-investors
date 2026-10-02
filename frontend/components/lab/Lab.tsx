"use client";

import { useLab } from "@/lib/api/hooks";
import { useT } from "@/lib/useT";
import { LabExtractor } from "./LabExtractor";
import { LabFrame } from "./LabFrame";
import { LabHindi, LabRetrieval } from "./LabRetrieval";
import { LabVerifier, LabWeak } from "./LabVerifier";

const REPO = "https://github.com/AkshatTm/FinSight-IPO-X-Ray-for-Indian-retail-investors";

/** Model Lab (spec section 8). Every section reads its own file and hides when the data is missing. */
export function Lab() {
  const { t } = useT();
  const ladder = useLab("ladder");
  const weak = useLab("weaklabels");
  const verifier = useLab("verifier");
  const retrieval = useLab("retrieval");
  const asr = useLab("asr");
  const frontier = useLab("frontier");
  const loading = [ladder, weak, verifier, retrieval, asr].every((q) => q.isPending);

  return (
    <div className="py-12 md:py-16">
      <h1 className="text-[2.25rem] font-semibold leading-tight tracking-tight md:text-[3rem]">{t("lab.title")}</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">{t("lab.intro")}</p>
      {loading ? (
        <div aria-hidden className="mt-12 space-y-4">
          <div className="h-8 w-64 animate-pulse rounded bg-surface-2" />
          <div className="h-48 animate-pulse rounded-[10px] bg-surface-2" />
        </div>
      ) : (
        <>
          <LabExtractor data={ladder.data} />
          <LabWeak data={weak.data} />
          <LabVerifier data={verifier.data} />
          <LabRetrieval data={retrieval.data} />
          {frontier.data && (
            <LabFrame id="frontier" heading={t("lab.front.h")} shows={t("lab.front.shows")}>
              <p className="text-muted">{t("lab.missing")}</p>
            </LabFrame>
          )}
          <LabHindi asr={asr.data} retrieval={retrieval.data} />
        </>
      )}
      <p className="mt-16 max-w-2xl border-t border-rule pt-6 text-muted">
        {t("lab.foot")}{" "}
        <a href={REPO} target="_blank" rel="noreferrer" className="text-stamp underline underline-offset-4">
          {t("lab.foot.link")}
        </a>
      </p>
    </div>
  );
}
