import type { Metadata } from "next";
import { UploadPage } from "@/components/upload/UploadPage";

export const metadata: Metadata = { title: "Analyse a document" };

export default function Page() {
  return <UploadPage />;
}
