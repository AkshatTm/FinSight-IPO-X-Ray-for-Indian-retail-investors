"use client";

import { create } from "zustand";
import { ApiError } from "@/lib/api/client";
import { applyEvent, newTurn, type Turn } from "@/lib/chat";
import type { Lang } from "@/lib/format";
import { streamChat } from "@/lib/sse";

export interface EvidenceRef {
  ipoId: string;
  turnId: string;
  index: number;
}

interface ChatState {
  turns: Record<string, Turn[]>;
  evidence: EvidenceRef | null;
  /** Unsent composer text per IPO; survives tab switches. */
  drafts: Record<string, { text: string; voice: boolean }>;
  setDraft: (ipoId: string, text: string, voice?: boolean) => void;
  ask: (ipoId: string, question: string, language: Lang, source?: "typed" | "voice" | "chip") => Promise<void>;
  openEvidence: (e: EvidenceRef) => void;
  closeEvidence: () => void;
  reset: (ipoId: string) => void;
}

let counter = 0;

export const useChat = create<ChatState>()((set, get) => {
  const patch = (ipoId: string, id: string, fn: (t: Turn) => Turn) =>
    set((s) => ({ turns: { ...s.turns, [ipoId]: (s.turns[ipoId] ?? []).map((t) => (t.id === id ? fn(t) : t)) } }));

  return {
    turns: {},
    evidence: null,
    drafts: {},
    setDraft: (ipoId, text, voice = false) => set((s) => ({ drafts: { ...s.drafts, [ipoId]: { text, voice } } })),
    openEvidence: (evidence) => set({ evidence }),
    closeEvidence: () => set({ evidence: null }),
    reset: (ipoId) => set((s) => ({ turns: { ...s.turns, [ipoId]: [] }, evidence: null })),

    async ask(ipoId, question, language, source = "typed") {
      const q = question.trim();
      if (!q) return;
      if ((get().turns[ipoId] ?? []).some((t) => t.status === "streaming")) return;
      const id = `t${++counter}`;
      set((s) => ({ turns: { ...s.turns, [ipoId]: [...(s.turns[ipoId] ?? []), newTurn(id, ipoId, q, language)] } }));
      try {
        const demo = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("demo") === "1";
        for await (const ev of streamChat({ ipo_id: ipoId, question: q, language, source, demo })) {
          patch(ipoId, id, (t) => applyEvent(t, ev));
        }
        patch(ipoId, id, (t) =>
          t.status !== "streaming"
            ? t
            : t.answer || t.guard || t.abstain
              ? { ...t, status: "done", stage: null }
              : { ...t, status: "error", stage: null, error: { code: "internal_error" } },
        );
      } catch (e) {
        const code = e instanceof ApiError ? e.code : "network";
        patch(ipoId, id, (t) => ({ ...t, status: "error", stage: null, error: { code } }));
      }
    },
  };
});
