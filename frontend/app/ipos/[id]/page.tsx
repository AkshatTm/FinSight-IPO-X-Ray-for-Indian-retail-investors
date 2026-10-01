import type { Metadata } from "next";
import { Workspace } from "@/components/workspace/Workspace";

export const metadata: Metadata = { title: "Workspace" };

export default async function WorkspacePage({ params }: PageProps<"/ipos/[id]">) {
  const { id } = await params;
  return <Workspace id={id} />;
}
