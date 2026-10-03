import type { Metadata } from "next";
import { ReportPage } from "@/components/reports/ReportPage";

export const metadata: Metadata = { title: "Report" };

export default async function Page({ params }: PageProps<"/reports/[doc_id]">) {
  const { doc_id } = await params;
  return <ReportPage docId={doc_id} />;
}
