import type { Metadata } from "next";
import { LibraryView } from "@/components/library/LibraryView";

export const metadata: Metadata = { title: "IPOs" };

export default function IposPage() {
  return <LibraryView />;
}
