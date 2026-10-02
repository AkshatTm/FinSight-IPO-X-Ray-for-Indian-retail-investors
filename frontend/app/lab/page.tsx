import type { Metadata } from "next";
import { Lab } from "@/components/lab/Lab";

export const metadata: Metadata = { title: "Model Lab" };

export default function Page() {
  return <Lab />;
}
