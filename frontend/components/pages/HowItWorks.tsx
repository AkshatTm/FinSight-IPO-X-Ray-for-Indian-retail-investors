"use client";

import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import { apiGet, type Schemas } from "@/lib/api/client";
import { STRINGS, type StringKey } from "@/lib/copy";
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

function Flow({ prefix, count, heading, title, image }: { prefix: Prefix; count: number; heading: string; title?: (n: number) => string; image?: { src: string; alt: string } }) {
  const { t } = useT();
  const body = (n: number) => `how.${prefix}${n}.b`;
  const steps = Array.from({ length: count }, (_, i) => i + 1);
  return (
    <section aria-label={heading} className="mt-12 grid gap-x-12 gap-y-5 border-t border-rule pt-8 md:grid-cols-[minmax(0,5fr)_minmax(0,8fr)]">
      <div>
        <h2 className="font-serif text-xl font-semibold tracking-tight">{heading}</h2>
        {image && (
          <Image src={image.src} alt={image.alt} width={800} height={600} sizes="(min-width: 768px) 360px, 100vw" className="mt-4 hidden aspect-[4/3] w-full max-w-[360px] rounded-[6px] border border-rule object-cover md:block" />
        )}
      </div>
      <ol className="divide-y divide-rule">
        {steps.map((n) => (
          <li key={n} className="grid grid-cols-[2rem_1fr] gap-x-3 py-4 first:pt-0 last:pb-0">
            <span className="num pt-0.5 font-serif text-lg text-muted">{n}</span>
            <div>
              <h3 className="font-semibold">{title ? title(n) : t(`how.${prefix}${n}.h` as StringKey)}</h3>
              {body(n) in STRINGS && <p className="mt-1 max-w-[62ch] text-muted">{t(body(n) as StringKey)}</p>}
              {EXAMPLE[`${prefix}${n}`] && (
                <Link
                  href={`/ipos/${EXAMPLE[`${prefix}${n}`].ipo}`}
                  className="mt-2 inline-flex min-h-11 items-center text-sm text-stamp underline underline-offset-4"
                >
                  {t(EXAMPLE[`${prefix}${n}`].key)}
                </Link>
              )}
            </div>
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
  return <Flow prefix="r" count={8} heading={t("how.row3")} title={title} image={{ src: "/images/how-dawn.webp", alt: "A hazy city skyline across the water at sunrise." }} />;
}

export function HowItWorks() {
  const { t } = useT();
  return (
    <div className="py-12 md:py-16">
      <h1 className="font-serif text-3xl font-semibold leading-tight tracking-tight md:text-[2.5rem]">{t("how.title")}</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">{t("how.intro")}</p>
      <Flow prefix="p" count={6} heading={t("how.row1")} image={{ src: "/images/how-documents.webp", alt: "A tall stack of printed offer documents with a blue paper clip on the top page." }} />
      <Flow prefix="q" count={5} heading={t("how.row2")} image={{ src: "/images/how-ledger.webp", alt: "An open ledger with a brass magnifying glass resting on its ruled page." }} />
      <UploadFlow />
      <section className="mt-12 grid gap-x-12 border-t border-rule pt-8 md:grid-cols-[minmax(0,5fr)_minmax(0,8fr)]">
        <span aria-hidden />
        {([1, 2, 3] as const).map((n) => (
          <div key={n} className="border-b border-rule py-5 first:pt-0 md:col-start-2">
            <h2 className="font-semibold">{t(`how.faq${n}.q` as StringKey)}</h2>
            <p className="mt-2 text-muted">{t(`how.faq${n}.a` as StringKey)}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
