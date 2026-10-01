"use client";

import Link from "next/link";
import { useT } from "@/lib/useT";

/** 404 and 500 pages (spec 11): one heading, one line, one button. */
export function Notice({ kind, onReload }: { kind: "404" | "500"; onReload?: () => void }) {
  const { t } = useT();
  const btn = "mt-8 inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-bg transition-transform duration-150 active:scale-[0.97]";
  return (
    <div className="py-20 md:py-28">
      <h1 className="max-w-2xl text-[2.25rem] font-semibold leading-tight tracking-tight">
        {kind === "404" ? t("nf.title") : t("err500.title")}
      </h1>
      <p className="mt-4 max-w-xl text-lg text-muted">{kind === "404" ? t("nf.body") : t("err500.body")}</p>
      {kind === "404" ? (
        <Link href="/ipos" className={btn}>
          {t("nf.cta")}
        </Link>
      ) : (
        <button type="button" onClick={onReload ?? (() => window.location.reload())} className={btn}>
          {t("err500.cta")}
        </button>
      )}
    </div>
  );
}
