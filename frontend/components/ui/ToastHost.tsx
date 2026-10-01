"use client";

import { useToast } from "@/lib/toast";

export function ToastHost() {
  const message = useToast((s) => s.message);
  return (
    <div aria-live="polite" role="status" className="pointer-events-none fixed bottom-4 right-4 z-50 max-w-[calc(100vw-2rem)]">
      {message && (
        <p className="toast-in rounded-[10px] border border-rule bg-surface px-4 py-3 text-sm shadow-[var(--shadow-float)]">
          {message}
        </p>
      )}
    </div>
  );
}
