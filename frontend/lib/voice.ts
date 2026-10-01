// Voice input state machine (spec 7.5.6). Pure so it can be unit-tested; the hook lives in useVoice.
import type { Lang } from "@/lib/format";

export const MAX_RECORD_MS = 20_000;

export type VoiceState = "idle" | "permission" | "recording" | "transcribing" | "done" | "tooLong" | "failed" | "blocked";

export type VoiceEvent =
  | { type: "tap" }
  | { type: "granted" }
  | { type: "denied" }
  | { type: "stop"; elapsedMs: number }
  | { type: "transcribed" }
  | { type: "error" }
  | { type: "reset" };

/** Tap starts or stops; a recording longer than 20 s is discarded and the user is told to retry. */
export function voiceReducer(state: VoiceState, ev: VoiceEvent): VoiceState {
  switch (ev.type) {
    case "tap":
      if (state === "recording") return state;
      if (state === "permission" || state === "transcribing") return state;
      return "permission";
    case "granted":
      return state === "permission" ? "recording" : state;
    case "denied":
      return "blocked";
    case "stop":
      if (state !== "recording") return state;
      return ev.elapsedMs > MAX_RECORD_MS ? "tooLong" : "transcribing";
    case "transcribed":
      return state === "transcribing" ? "done" : state;
    case "error":
      return "failed";
    case "reset":
      return "idle";
  }
}

/** A Hindi transcript (any Devanagari) switches the answer language to Hindi. */
export function answerLanguage(transcript: string, current: Lang): Lang {
  return /[ऀ-ॿ]/.test(transcript) ? "hi" : current;
}

export function pickMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].find((m) => MediaRecorder.isTypeSupported?.(m));
}
