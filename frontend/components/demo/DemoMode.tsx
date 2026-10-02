"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { GlassSurface } from "@/components/glass/GlassSurface";
import { apiGet } from "@/lib/api/client";
import type { components } from "@/lib/api/types";
import { useChat } from "@/lib/chatStore";
import {
  DEMO_AUDIO, DEMO_IPO, DEMO_QUESTIONS, firstContradicted, isDemoSearch, isTypingTarget,
  stepForKey, trickQuestion, type DemoStep,
} from "@/lib/demo";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";

type Suggested = components["schemas"]["SuggestedQuestion"];

// Once ?demo=1 has been seen, demo mode stays on for the session even after a link drops the query.
let sticky = false;
const subscribe = (cb: () => void) => {
  window.addEventListener("popstate", cb);
  return () => window.removeEventListener("popstate", cb);
};
const snapshot = () => (sticky ||= isDemoSearch(window.location.search));

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function waitFor<T extends Element>(selector: string, ms = 8000): Promise<T | null> {
  for (let t = 0; t < ms; t += 100) {
    const el = document.querySelector<T>(selector);
    if (el) return el;
    await wait(100);
  }
  return null;
}

/** Spec 16: scripted tour on hotkeys 1 to 7 (0 resets). Answers replay from the backend demo cache. */
export function DemoMode() {
  const demo = useSyncExternalStore(subscribe, snapshot, () => false);
  const router = useRouter();
  const client = useQueryClient();
  const { t } = useT();
  const [step, setStep] = useState<DemoStep>(0);
  // Hotkeys queue up: a second press waits for the first step (e.g. a streaming answer) to finish.
  const queue = useRef<Promise<void>>(Promise.resolve());

  const workspace = useCallback(async () => {
    if (!window.location.pathname.startsWith(`/ipos/${DEMO_IPO}`)) router.push(`/ipos/${DEMO_IPO}?demo=1`);
    await waitFor("[data-field]");
  }, [router]);

  const run = useCallback(
    async (n: DemoStep) => {
      const chat = useChat.getState();
      if (n === 0) {
        chat.reset(DEMO_IPO);
        chat.setDraft(DEMO_IPO, "");
        const ui = useUi.getState();
        ui.setInspector(false);
        ui.closeGlossary();
        ui.setHighlight(null);
        router.push("/ipos?demo=1");
      } else if (n === 1) {
        router.push(`/ipos/${DEMO_IPO}?demo=1`);
      } else if (n === 2) {
        await workspace();
        (await waitFor<HTMLButtonElement>('[data-field="fresh_issue_size"] button'))?.click();
      } else if (n === 3) {
        await workspace();
        await chat.ask(DEMO_IPO, DEMO_QUESTIONS.money, "en", "chip");
      } else if (n === 4) {
        await workspace();
        const qs = await client.fetchQuery({
          queryKey: ["suggested", DEMO_IPO],
          queryFn: () => apiGet<Suggested[]>(`/api/ipos/${DEMO_IPO}/suggested-questions`),
        });
        const q = trickQuestion(qs);
        if (!q) return;
        await chat.ask(DEMO_IPO, q, "en", "chip");
        const turn = useChat.getState().turns[DEMO_IPO]?.at(-1);
        const index = firstContradicted(turn);
        if (turn && index !== null) chat.openEvidence({ ipoId: DEMO_IPO, turnId: turn.id, index });
      } else if (n === 5) {
        await workspace();
        // The recorded Hindi question goes through the real speech recognition; the transcript lands in
        // the question box and is not sent until the presenter does it (voice never auto-sends).
        const clip = await (await fetch(DEMO_AUDIO)).blob();
        void new Audio(URL.createObjectURL(clip)).play().catch(() => {});
        const body = new FormData();
        body.append("audio", clip, "hi_q02.m4a");
        body.append("language", "hi");
        const res = await fetch("/api/voice", { method: "POST", body });
        const text = res.ok ? (((await res.json()) as { transcript?: string }).transcript ?? "").trim() : "";
        if (text) chat.setDraft(DEMO_IPO, text, true);
      } else if (n === 6) {
        await workspace();
        await chat.ask(DEMO_IPO, DEMO_QUESTIONS.advice, "en", "chip");
      } else {
        router.push("/lab?demo=1");
      }
    },
    [client, router, workspace],
  );

  useEffect(() => {
    if (!demo) return;
    const onKey = (e: KeyboardEvent) => {
      const n = stepForKey(e);
      if (n === null || isTypingTarget(e.target)) return;
      queue.current = queue.current.then(async () => {
        setStep(n);
        await run(n).catch(() => {});
      });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [demo, run]);

  if (!demo) return null;
  return (
    <div className="pointer-events-none fixed bottom-4 left-4 z-40" role="status" aria-live="polite">
      <GlassSurface mode="css" cornerRadius={12} padding="10px 14px" className="text-sm">
        {t("demo.step", { n: step })}
      </GlassSurface>
    </div>
  );
}
