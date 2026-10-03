import type { Metadata } from "next";
import { MyUploads } from "@/components/me/MyUploads";

export const metadata: Metadata = { title: "My uploads" };

export default function Page() {
  return <MyUploads />;
}
