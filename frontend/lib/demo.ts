// Demo mode (spec 16): `?demo=1`, hotkeys 1 to 7 walk the scripted tour, 0 resets.
// The IPO is the one the demo cache is recorded on (scripts/record_demo.py, Ather Energy).
import type { Turn } from "@/lib/chat";

export const DEMO_IPO = "ather-energy-2025";
export const DEMO_STEPS = 7;
export const DEMO_QUESTIONS = {
  money: "What will the money be used for?",
  advice: "Should I apply for this IPO?",
} as const;
export const DEMO_AUDIO = "/demo/hi_q02.m4a";

export type DemoStep = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7;

export function isDemoSearch(search: string): boolean {
  return new URLSearchParams(search).get("demo") === "1";
}

/** Hotkey to step; 0 resets. Anything else (letters, modifiers, other digits) is not ours. */
export function stepForKey(e: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey">): DemoStep | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null;
  return /^[0-7]$/.test(e.key) ? (Number(e.key) as DemoStep) : null;
}

/** Typing in a field must never trigger a step. */
export function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName);
}

/** The trick question is the suggested one of kind "trick"; its number comes from the X-Ray. */
export function trickQuestion(qs: { text: string; kind: string }[] | undefined): string | null {
  return qs?.find((q) => q.kind === "trick")?.text ?? null;
}

/** Index of the first number FinSight marked wrong, so step 4 can open its drawer. */
export function firstContradicted(turn: Turn | undefined): number | null {
  return turn?.verdicts.find((v) => v.status === "contradicted")?.index ?? null;
}
