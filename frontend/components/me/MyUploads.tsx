"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { DocTypeBadge } from "@/components/reports/DocTypeBadge";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/supabase";
import type { StringKey } from "@/lib/i18n";
import { useT } from "@/lib/useT";

const STATUS: Record<string, StringKey> = {
  processing: "me.processing",
  ready: "me.ready",
  partial: "me.partial",
  failed: "me.failed",
};

/** /me/uploads (B05 §6.2). */
export function MyUploads() {
  const { t, lang } = useT();
  const { user, token, ready, signIn } = useAuth();
  const q = useQuery({
    queryKey: ["me-uploads", user?.id],
    enabled: !!user,
    queryFn: () => apiGet<Schemas["MyUpload"][]>("/api/me/uploads", token ? { headers: { Authorization: `Bearer ${token}` } } : undefined),
  });
  const btn = "btn inline-flex h-11 items-center rounded-[6px] bg-stamp px-5 font-medium text-bg";

  return (
    <div className="mx-auto max-w-[1120px] py-12">
      <h1 className="text-[2rem] font-semibold leading-tight tracking-tight">{t("me.title")}</h1>
      {ready && !user && (
        <button type="button" onClick={() => void signIn("/me/uploads")} className={`${btn} mt-6`}>
          {t("up.signInButton")}
        </button>
      )}
      {user && q.isPending && <div aria-busy className="mt-6 h-32 animate-pulse rounded-[10px] bg-surface-2 motion-reduce:animate-none" />}
      {user && q.isError && <div className="mt-6"><ErrorBlock error={q.error} onRetry={() => void q.refetch()} /></div>}
      {user && q.data?.length === 0 && (
        <div className="mt-6">
          <p className="text-muted">{t("me.empty")}</p>
          <Link href="/upload" className={`${btn} mt-4`}>{t("nav.analyse")}</Link>
        </div>
      )}
      {user && !!q.data?.length && (
        <table className="mt-6 w-full text-left text-sm">
          <thead className="border-b border-rule text-muted">
            <tr>
              <th className="py-2 font-medium">{t("me.company")}</th>
              <th className="py-2 font-medium">{t("me.type")}</th>
              <th className="py-2 font-medium">{t("me.uploaded")}</th>
              <th className="py-2 font-medium">{t("me.status")}</th>
              <th className="py-2"><span className="sr-only">{t("me.open")}</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {q.data.map((u) => (
              <tr key={u.doc_id}>
                <td className="py-3">{u.company ?? t("proc.yourDoc")}</td>
                <td className="py-3">{u.doc_type ? <DocTypeBadge type={u.doc_type} /> : null}</td>
                <td className="py-3 tabular-nums">{new Date(u.created_at).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric" })}</td>
                <td className="py-3">{STATUS[u.status] ? t(STATUS[u.status]) : u.status}</td>
                <td className="py-3 text-right">
                  <Link href={`/reports/${u.doc_id}`} className="text-stamp underline underline-offset-2">{t("me.open")}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
