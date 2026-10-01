"use client";

import { Microphone, Stop } from "@phosphor-icons/react";
import { GlassSurface } from "@/components/glass/GlassSurface";
import type { VoiceApi } from "@/lib/useVoice";
import { useT } from "@/lib/useT";

/** Round mic button (glass where supported). Level ring while recording; text status lives in VoiceStatus. */
export function MicButton({ voice }: { voice: VoiceApi }) {
  const { t } = useT();
  const recording = voice.state === "recording";
  const busy = voice.state === "permission" || voice.state === "transcribing";
  return (
    <GlassSurface mode="css" cornerRadius={22} className="h-11 w-11 shrink-0">
      <button
        type="button"
        onClick={voice.toggle}
        disabled={busy}
        aria-pressed={recording}
        aria-label={recording ? t("voice.recording") : t("voice.idle")}
        title={t("voice.idle")}
        className="relative inline-flex h-full w-full items-center justify-center rounded-full text-text disabled:opacity-50"
      >
        {recording && (
          <span
            aria-hidden
            className="absolute inset-0 rounded-full border-2 border-stamp"
            style={{ transform: `scale(${1 + voice.level * 0.25})`, opacity: 0.4 + voice.level * 0.6 }}
          />
        )}
        {recording ? <Stop size={20} weight="fill" /> : <Microphone size={20} />}
      </button>
    </GlassSurface>
  );
}

const MESSAGE = {
  permission: "voice.permission",
  recording: "voice.recording",
  transcribing: "voice.transcribing",
  done: "voice.done",
  tooLong: "voice.tooLong",
  failed: "voice.failed",
  blocked: "voice.blocked",
} as const;

export function VoiceStatus({ voice }: { voice: VoiceApi }) {
  const { t } = useT();
  if (voice.state === "idle") return <p className="sr-only" role="status" aria-live="polite" />;
  const secs = Math.floor(voice.elapsedMs / 1000);
  return (
    <p className="mt-2 text-sm text-muted" role="status" aria-live="polite">
      {t(MESSAGE[voice.state])}
      {voice.state === "recording" && <span className="ml-2 font-mono">{`0:${String(secs).padStart(2, "0")} / 0:20`}</span>}
    </p>
  );
}
