"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { apiGet, type Schemas } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/supabase";
import { useT } from "@/lib/useT";

type Costs = Schemas["CostSummary"];
type Failed = Schemas["FailedJob"];

const num = (n: number) => Math.round(n).toLocaleString("en-IN");
const usd = (n: number) => `$${n.toFixed(2)}`;
const pct = (share: number) => `${(share * 100).toFixed(2)}%`;

/** The cost table and failed-job list, given the two admin responses (B06 §6). */
export function CostsView({ costs, failed }: { costs: Costs; failed: Failed[] }) {
  const { t } = useT();
  const th = "py-2 pr-4 font-medium";
  const td = "py-2 pr-4 tabular-nums";
  return (
    <>
      <p className="mt-2 text-muted">{t("admin.intro")}</p>
      {costs.provisional && <p className="mt-2 text-sm text-muted">{t("admin.provisional")}</p>}
      {costs.usd_incomplete && <p className="mt-2 text-sm text-query">{t("admin.usdIncomplete")}</p>}

      <h2 className="mt-8 text-xl font-semibold">{t("admin.window", { n: costs.window_days })}</h2>
      <p className="mt-1 text-sm">
        {t("admin.freeShare", { vcpu: pct(costs.total.free_vcpu_share), gib: pct(costs.total.free_gib_share) })}
      </p>
      {costs.days.length === 0 ? (
        <p className="mt-4 text-muted">{t("admin.noJobs")}</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-rule text-muted">
              <tr>
                <th className={th}>{t("admin.date")}</th>
                <th className={th}>{t("admin.uploads")}</th>
                <th className={th}>{t("admin.jobs")}</th>
                <th className={th}>{t("admin.failed")}</th>
                <th className={th}>{t("admin.vcpu")}</th>
                <th className={th}>{t("admin.gib")}</th>
                <th className={th}>{t("admin.gpu")}</th>
                <th className={th}>{t("admin.usd")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {costs.days.map((d) => (
                <tr key={d.date}>
                  <td className={td}>{d.date}</td>
                  <td className={td}>{d.uploads}</td>
                  <td className={td}>{d.jobs}</td>
                  <td className={td}>{d.failed}</td>
                  <td className={td}>{num(d.vcpu_s)}</td>
                  <td className={td}>{num(d.gib_s)}</td>
                  <td className={td}>{num(d.gpu_s)}</td>
                  <td className={td}>{usd(d.usd)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t border-rule font-medium">
              <tr>
                <td className={td} />
                <td className={td}>{costs.total.uploads}</td>
                <td className={td}>{costs.total.jobs}</td>
                <td className={td} />
                <td className={td}>{num(costs.total.vcpu_s)}</td>
                <td className={td}>{num(costs.total.gib_s)}</td>
                <td className={td} />
                <td className={td}>{usd(costs.total.usd)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <h2 className="mt-10 text-xl font-semibold">{t("admin.failedTitle")}</h2>
      {failed.length === 0 ? (
        <p className="mt-4 text-muted">{t("admin.noFailed")}</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-rule text-muted">
              <tr>
                <th className={th}>{t("admin.document")}</th>
                <th className={th}>{t("admin.stage")}</th>
                <th className={th}>{t("admin.error")}</th>
                <th className={th}>{t("admin.date")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {failed.map((f) => (
                <tr key={f.job.job_id}>
                  <td className="py-2 pr-4">
                    <Link href={`/reports/${f.job.doc_id}`} className="text-stamp underline underline-offset-2">
                      {f.company ?? f.job.doc_id}
                    </Link>
                  </td>
                  <td className="py-2 pr-4">{f.job.stage}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{f.job.error ?? "—"}</td>
                  <td className={td}>{new Date(f.created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/** /admin/costs (B02 §12, B06 §6): admin allow-list only; others see the API's 403 message. */
export function AdminCosts() {
  const { t } = useT();
  const { user, token, ready, signIn } = useAuth();
  const init = token ? { headers: { Authorization: `Bearer ${token}` } } : undefined;
  const q = useQuery({
    queryKey: ["admin-costs", user?.id],
    enabled: !!user,
    retry: false,
    queryFn: async () => {
      const [costs, failed] = await Promise.all([
        apiGet<Costs>("/api/admin/costs", init),
        apiGet<Failed[]>("/api/admin/jobs?status=failed", init),
      ]);
      return { costs, failed };
    },
  });

  return (
    <div className="mx-auto max-w-[1120px] py-12">
      <h1 className="text-[2rem] font-semibold leading-tight tracking-tight">{t("admin.title")}</h1>
      {ready && !user && (
        <div className="mt-6">
          <p className="text-muted">{t("admin.signIn")}</p>
          <button
            type="button"
            onClick={() => void signIn("/admin/costs")}
            className="btn mt-4 inline-flex h-11 items-center rounded-[6px] bg-stamp px-5 font-medium text-bg"
          >
            {t("up.signInButton")}
          </button>
        </div>
      )}
      {user && q.isPending && <div aria-busy className="mt-6 h-32 animate-pulse rounded-[10px] bg-surface-2 motion-reduce:animate-none" />}
      {user && q.isError && <div className="mt-6"><ErrorBlock error={q.error} onRetry={() => void q.refetch()} /></div>}
      {user && q.data && <CostsView costs={q.data.costs} failed={q.data.failed} />}
    </div>
  );
}
