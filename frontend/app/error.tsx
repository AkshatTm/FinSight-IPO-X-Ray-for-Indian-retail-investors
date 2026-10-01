"use client";

import { Notice } from "@/components/pages/Notice";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return <Notice kind="500" onReload={reset} />;
}
