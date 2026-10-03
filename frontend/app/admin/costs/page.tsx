import type { Metadata } from "next";
import { AdminCosts } from "@/components/admin/AdminCosts";

export const metadata: Metadata = { title: "Costs", robots: { index: false } };

export default function Page() {
  return <AdminCosts />;
}
