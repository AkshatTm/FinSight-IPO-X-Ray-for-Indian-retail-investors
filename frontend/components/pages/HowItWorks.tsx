"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiGet, type Schemas } from "@/lib/api/client";
import { STRINGS, type StringKey } from "@/lib/i18n";
import { SAMPLE_REPORT_DOC_ID } from "@/lib/showcase";
import { useT } from "@/lib/useT";

/** Each step points at a real, already-built IPO so the box can be checked against a page. */
const EXAMPLE: Record<string, { ipo: string; key: StringKey }> = {
  p1: { ipo: "ather-energy-2025", key: "how.link.ather" },
  p2: { ipo: "ather-energy-2025", key: "how.link.ather" },
  p3: { ipo: "ather-energy-2025", key: "how.link.ather" },
  p4: { ipo: "ather-energy-2025", key: "how.link.ather" },
  p5: { ipo: "ather-energy-2025", key: "how.link.ather" },
  p6: { ipo: "lenskart-2025", key: "how.link.lenskart" },
  q1: { ipo: "lenskart-2025", key: "how.link.lenskart" },
  q2: { ipo: "lenskart-2025", key: "how.link.lenskart" },
  q3: { ipo: "lenskart-2025", key: "how.link.lenskart" },
  q4: { ipo: "ather-energy-2025", key: "how.link.ather" },
  q5: { ipo: "ather-energy-2025", key: "how.link.ather" },
};

type Prefix = "p" | "q" | "r";

function Flow({ prefix, count, heading, title }: { prefix: Prefix; count: number; heading: string; title?: (n: number) => string }) {
  const { t } = useT();
  const body = (n: number) => `how.${prefix}${n}.b`;
  const steps = Array.from({ length: count }, (_, i) => i + 1);
  return (
    <section aria-label={heading} className="mt-12">
      <h2 className="text-xl font-semibold">{heading}</h2>
      <ol className={`mt-5 grid gap-3 sm:grid-cols-2 ${count > 6 ? "lg:grid-cols-4" : "lg:grid-flow-col lg:auto-cols-fr"}`}>
        {steps.map((n) => (
          <li key={n} className="relative rounded-[10px] border border-rule bg-surface p-4">
            <span className="grid h-7 w-7 place-items-center rounded-full border border-rule font-mono text-xs">{n}</span>
            <h3 className="mt-3 font-semibold">{title ? title(n) : t(`how.${prefix}${n}.h` as StringKey)}</h3>
            {body(n) in STRINGS && <p className="mt-1 text-sm text-muted">{t(body(n) as StringKey)}</p>}
            {EXAMPLE[`${prefix}${n}`] && (
              <Link
                href={`/ipos/${EXAMPLE[`${prefix}${n}`].ipo}`}
                className="mt-3 inline-flex min-h-11 items-center text-sm text-stamp underline underline-offset-4"
              >
                {t(EXAMPLE[`${prefix}${n}`].key)}
              </Link>
            )}
            {n < count && count <= 6 && (
              <svg aria-hidden viewBox="0 0 24 24" className="absolute -right-[14px] top-1/2 z-10 hidden h-6 w-6 -translate-y-1/2 text-muted lg:block" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 12h10M13 8l4 4-4 4" />
              </svg>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

/** B05 §8 row 3. Step 6 names `corpus_n` from the risk-level endpoint (configs/risklevel.yaml);
 * while that is 0 (placeholder thresholds) the step is shown without a number. */
function UploadFlow() {
  const { t } = useT();
  const level = useQuery({
    queryKey: ["risk-level", SAMPLE_REPORT_DOC_ID],
    queryFn: () => apiGet<Schemas["RiskLevel"]>(`/api/docs/${SAMPLE_REPORT_DOC_ID}/risk-level`),
    retry: false,
  }).data;
  const n = level?.corpus_n ?? 0;
  const title = (step: number) =>
    step === 6 ? (n > 0 ? t("how.r6.h", { n: n.toLocaleString("en-US") }) : t("how.r6.h0")) : t(`how.r${step}.h` as StringKey);
  return <Flow prefix="r" count={8} heading={t("how.row3")} title={title} />;
}

export function HowItWorks() {
  const { t } = useT();
  return (
    <div className="py-12 md:py-16">
      <h1 className="text-[2.25rem] font-semibold leading-tight tracking-tight md:text-[3rem]">{t("how.title")}</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">{t("how.intro")}</p>
      <Flow prefix="p" count={6} heading={t("how.row1")} />
      <Flow prefix="q" count={5} heading={t("how.row2")} />
      <UploadFlow />
      <section className="mt-16 max-w-2xl border-t border-rule pt-4">
        {([1, 2, 3] as const).map((n) => (
          <div key={n} className="border-b border-rule py-5">
            <h2 className="font-semibold">{t(`how.faq${n}.q` as StringKey)}</h2>
            <p className="mt-2 text-muted">{t(`how.faq${n}.a` as StringKey)}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
