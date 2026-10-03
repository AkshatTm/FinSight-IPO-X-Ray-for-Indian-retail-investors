"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth/supabase";
import type { StringKey } from "@/lib/i18n";
import { useToast } from "@/lib/toast";
import { rejectionFor, uploadDocument, UploadError, type UploadPhase } from "@/lib/upload";
import { useT } from "@/lib/useT";
import { DropZone } from "./DropZone";
import { useLimits } from "./useLimits";

/** /upload (B05 §3): sign in, drop a PDF, hash, upload, then open the report or show why not. */
export function UploadPage() {
  const { t } = useT();
  const router = useRouter();
  const limits = useLimits();
  const { user, token, signIn } = useAuth();
  const toast = useToast((s) => s.show);
  const [phase, setPhase] = useState<UploadPhase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const paused = !limits.enabled || error === "uploads_disabled";

  const onFile = async (file: File) => {
    setError(null);
    try {
      const out = await uploadDocument(file, { token, maxMb: limits.max_mb, onPhase: setPhase });
      if (out.kind === "exists") toast(t("up.duplicate"));
      router.push(`/reports/${out.docId}`);
    } catch (e) {
      setError(e instanceof UploadError ? e.code : "internal_error");
      setPhase(null);
    }
  };

  const rejection = error ? rejectionFor(error) : null;
  const message = rejection
    ? t(`rej.${rejection}` as StringKey, { max_mb: limits.max_mb })
    : error && error !== "uploads_disabled"
      ? t("err.internal_error")
      : null;

  return (
    <div className="mx-auto max-w-2xl py-12 md:py-16">
      <h1 className="text-[2rem] font-semibold leading-tight tracking-tight">{t("up.title")}</h1>
      <p className="mt-3 text-lg text-muted">{t("up.sub")}</p>

      <div className="mt-8">
        <DropZone disabled={!user || paused} busy={phase !== null} maxMb={limits.max_mb} onFile={(f) => void onFile(f)} />
      </div>

      {phase && (
        <p role="status" className="mt-3 text-sm text-muted">
          {t(phase === "hashing" ? "up.hashing" : "up.sending")}
        </p>
      )}
      {message && (
        <p role="alert" data-testid="rejection" className="mt-4 rounded-[8px] border border-rule bg-surface-2 p-4 text-sm">
          {message}
        </p>
      )}

      {paused ? (
        <p className="mt-6 text-sm">
          {t("up.paused")}{" "}
          <Link href="/ipos" className="text-stamp underline underline-offset-2">
            {t("nav.ipos")}
          </Link>
        </p>
      ) : !user ? (
        <div className="mt-6">
          <button
            type="button"
            onClick={() => void signIn("/upload")}
            className="btn inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-bg"
          >
            {t("up.signInButton")}
          </button>
          <p className="mt-2 text-sm text-muted">{t("up.signInWhy")}</p>
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted">{t("up.limits")}</p>
      )}

      <p className="mt-4 text-xs text-muted">{t("up.consent")}</p>

      <details className="mt-8 rounded-[8px] border border-rule bg-surface p-4">
        <summary className="cursor-pointer text-sm font-medium">{t("up.where")}</summary>
        <p className="mt-2 text-sm text-muted">{t("up.whereBody")}</p>
      </details>
    </div>
  );
}
